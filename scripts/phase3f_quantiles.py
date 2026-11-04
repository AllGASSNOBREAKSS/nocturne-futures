"""Rolling and volatility-conditional range-quantile recalibration.

Adds no new label. Test-day adjustments use only residuals from strictly earlier
days (one-day gap), so the procedure is time-series-aware rather than a random
split-conformal claim.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from nocturne.adapters.history import checksum
from nocturne.research.hourly_dataset import FEATURES
from nocturne.research.validation import block_mean_interval, reserve_holdout, walk_forward

ROOT = Path(__file__).resolve().parents[1]
QUANTILES = (.5, .8, .9)
BUCKETS = 3
MIN_RESIDUALS = 200


def fit_quantile(train, quantile):
    model = make_pipeline(SimpleImputer(), LGBMRegressor(objective="quantile", alpha=quantile,
        n_estimators=100, num_leaves=7, learning_rate=.05, min_child_samples=50,
        random_state=7, n_jobs=1, verbosity=-1))
    return model.fit(train[FEATURES], train.future_range)


def rearrange(values):
    return np.sort(np.maximum(values, 0), axis=1)


def main():
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "protocol": "phase3f-quantile-recalibration-v1",
              "event": "next_two_contiguous_hourly_bars_high_minus_low",
              "methods": ["unconditional_train_quantile", "global_residual",
                          "rolling_residual_one_day_gap", "volatility_bucket_residual"],
              "instruments": {}}
    for instrument in ("NQ", "ES"):
        path = ROOT / f"data/research/{instrument}_two_hour_phase3f.csv"
        data = pd.read_csv(path)
        data["atr_pct"] = pd.to_numeric(data.atr_pct, errors="coerce")
        dev, _ = reserve_holdout(data)
        folds = walk_forward(dev, min_train=60, calibration_groups=20, test_groups=30)
        rows = []
        for fold_index, fold in enumerate(folds):
            train, cal, test = fold.train, fold.calibration, fold.test
            edges = train.atr_pct.quantile(np.linspace(0, 1, BUCKETS + 1)).to_numpy()
            bucket = lambda frame: np.clip(np.searchsorted(edges[1:-1], frame.atr_pct.to_numpy()), 0, BUCKETS - 1)
            predictions = {}
            for quantile in QUANTILES:
                model = fit_quantile(train, quantile)
                predictions[quantile] = {
                    "train": model.predict(test[FEATURES]),
                    "cal": model.predict(cal[FEATURES]),
                    "test": model.predict(test[FEATURES]),
                }
            test = test.copy()
            test["bucket"] = bucket(test)
            test["fold"] = fold_index
            test["actual"] = test.future_range.to_numpy()
            # Baseline: unconditional train quantile.
            baseline = np.column_stack([np.full(len(test), np.quantile(train.future_range, q)) for q in QUANTILES])
            # Global residual calibration on the 20-day calibration block.
            global_pred = np.column_stack([
                predictions[q]["test"] + np.quantile(cal.future_range.to_numpy() - predictions[q]["cal"], q)
                for q in QUANTILES])
            # Rolling residual calibration with a one-day gap, expanding history.
            rolling_pred = np.full((len(test), len(QUANTILES)), np.nan)
            history = pd.DataFrame({"day": cal.day.to_numpy(), "actual": cal.future_range.to_numpy(),
                                    **{f"p{q}": predictions[q]["cal"] for q in QUANTILES}})
            for day in sorted(test.day.unique()):
                mask = test.day.to_numpy() == day
                prior_days = sorted(history.day.unique())
                usable = [d for d in prior_days if d < day]
                if usable:
                    subset = history[history.day.isin(usable)]
                else:
                    subset = history.iloc[0:0]
                if len(subset) >= MIN_RESIDUALS:
                    adjustments = [np.quantile(subset.actual.to_numpy() - subset[f"p{q}"].to_numpy(), q)
                                   for q in QUANTILES]
                else:
                    adjustments = [np.quantile(train.future_range, q) - predictions[q]["train"].mean()
                                   for q in QUANTILES]
                for j, q in enumerate(QUANTILES):
                    rolling_pred[mask, j] = predictions[q]["test"][mask] + adjustments[j]
                current = test[mask]
                history = pd.concat([history, pd.DataFrame({
                    "day": current.day.to_numpy(), "actual": current.future_range.to_numpy(),
                    **{f"p{q}": predictions[q]["test"][mask] for q in QUANTILES}})],
                    ignore_index=True)
            # Volatility-bucket residual calibration with global fallback.
            bucket_pred = np.full((len(test), len(QUANTILES)), np.nan)
            for b in range(BUCKETS):
                in_bucket = test.bucket.to_numpy() == b
                cal_bucket = bucket(cal) == b
                for j, q in enumerate(QUANTILES):
                    if cal_bucket.sum() >= MIN_RESIDUALS:
                        adjustment = np.quantile(
                            cal.future_range.to_numpy()[cal_bucket] - predictions[q]["cal"][cal_bucket], q)
                    else:
                        adjustment = np.quantile(
                            cal.future_range.to_numpy() - predictions[q]["cal"], q)
                    bucket_pred[in_bucket, j] = predictions[q]["test"][in_bucket] + adjustment
            for name, matrix in (("unconditional_train_quantile", baseline), ("global_residual", global_pred),
                                 ("rolling_residual_one_day_gap", rolling_pred),
                                 ("volatility_bucket_residual", bucket_pred)):
                matrix = rearrange(matrix)
                for j, q in enumerate(QUANTILES):
                    base = np.full(len(test), np.quantile(train.future_range, q))
                    base_loss = np.maximum(q * (test.actual - base), (q - 1) * (test.actual - base))
                    rows.append(pd.DataFrame({
                        "day": test.day, "fold": fold_index, "method": name, "quantile": q,
                        "actual": test.actual, "predicted": matrix[:, j],
                        "width": matrix[:, j], "covered": test.actual <= matrix[:, j],
                        "loss": np.maximum(q * (test.actual - matrix[:, j]),
                                           (q - 1) * (test.actual - matrix[:, j])),
                        "baseline_loss": base_loss, "bucket": test.bucket}))
        frame = pd.concat(rows, ignore_index=True)
        summary = {}
        for (method, quantile), group in frame.groupby(["method", "quantile"]):
            summary[f"{method}_{quantile}"] = {
                "n": len(group), "pinball_loss": float(group.loss.mean()),
                "baseline_loss": float(group.baseline_loss.mean()),
                "coverage": float(group.covered.mean()),
                "median_width": float(group.width.median()),
                "coverage_by_vol_bucket": {str(b): float(g.covered.mean())
                                           for b, g in group.groupby("bucket")},
                "paired_loss_interval": block_mean_interval(
                    group.loss.to_numpy() - group.baseline_loss.to_numpy(), group.day)}
        report["instruments"][instrument] = {"source_sha256": checksum(path), "summary": summary}
        frame.to_csv(ROOT / f"reports/phase3f_{instrument}_quantiles.csv.gz", index=False,
                     compression={"method": "gzip", "mtime": 0})
        print(instrument, {k: (round(v["pinball_loss"], 3), round(v["coverage"], 3))
                           for k, v in summary.items() if k.startswith("rolling")})
    (ROOT / "reports/phase3f_quantiles.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
