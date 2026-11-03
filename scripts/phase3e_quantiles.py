"""Time-separated range quantile calibration; research-only total range."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from nocturne.adapters.history import checksum
from nocturne.research.hourly_dataset import FEATURES
from nocturne.research.validation import reserve_holdout, walk_forward, block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
QUANTILES = (.5, .8, .9)


def main():
    report = {"decision": "NO_PROMOTION", "event": "next_two_contiguous_hourly_bars_high_minus_low",
              "holdout_scored": False, "protocol_sha256": checksum(ROOT / "docs/PHASE3E_RANGE_PROTOCOL.md"),
              "instruments": {}}
    for instrument in ("NQ", "ES"):
        path = ROOT / f"data/research/{instrument}_two_hour_phase3d.csv"
        dev, _ = reserve_holdout(pd.read_csv(path))
        folds = walk_forward(dev, min_train=60, calibration_groups=20, test_groups=30)
        rows, crossings, negatives = [], 0, 0
        for index, fold in enumerate(folds):
            train, cal, test = fold.train, fold.calibration, fold.test
            predictions = []
            for q in QUANTILES:
                model = make_pipeline(SimpleImputer(), LGBMRegressor(objective="quantile", alpha=q,
                    n_estimators=100, num_leaves=7, learning_rate=.05, min_child_samples=50,
                    random_state=7, n_jobs=1, verbosity=-1)).fit(train[FEATURES], train.future_range)
                adjustment = np.quantile(cal.future_range - model.predict(cal[FEATURES]), q)
                predictions.append(model.predict(test[FEATURES]) + adjustment)
            predicted = np.column_stack(predictions)
            crossings += int((np.diff(predicted, axis=1) < 0).any(axis=1).sum())
            negatives += int((predicted < 0).sum())
            predicted = np.sort(np.maximum(predicted, 0), axis=1)
            for j, q in enumerate(QUANTILES):
                y = test.future_range.to_numpy()
                baseline = np.quantile(train.future_range, q)
                residual, base_residual = y - predicted[:, j], y - baseline
                loss = np.maximum(q * residual, (q - 1) * residual)
                base_loss = np.maximum(q * base_residual, (q - 1) * base_residual)
                rows.append(pd.DataFrame(dict(day=test.day, signal_id=test.signal_id, fold=index,
                    quantile=q, actual=y, predicted=predicted[:, j], baseline=baseline,
                    loss=loss, delta_loss=loss-base_loss, covered=y <= predicted[:, j], baseline_covered=y <= baseline)))
        frame = pd.concat(rows, ignore_index=True)
        summary = {str(q): {"n": len(g), "pinball_loss": float(g.loss.mean()),
                   "coverage": float(g.covered.mean()), "baseline_coverage": float(g.baseline_covered.mean()),
                   "paired_loss_interval": block_mean_interval(g.delta_loss, g.day)} for q, g in frame.groupby("quantile")}
        report["instruments"][instrument] = {"source_sha256": checksum(path), "summary": summary,
                                             "raw_crossing_rows": crossings, "negative_values_clipped": negatives}
        frame.to_csv(ROOT / f"reports/phase3e_{instrument}_quantiles.csv.gz", index=False,
                     compression={"method": "gzip", "mtime": 0})
        print(instrument, {q: {"loss": v["pinball_loss"], "coverage": v["coverage"]} for q, v in summary.items()})
    (ROOT / "reports/phase3e_quantiles.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
