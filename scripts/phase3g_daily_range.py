"""Decades-long next-day range and expansion research on ^NDX.

Complements the direction study: activity should be predictable even when
direction is not. 2024 onward is reserved and unscored.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from nocturne.adapters.yahoo_history import load_history
from nocturne.ml.calibration import PlattCalibrator, classification_metrics
from nocturne.research.validation import block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"
FEATURES = ["ret_1_abs", "ret_5_abs", "vol_20", "vol_ratio", "atr_pct", "range_atr",
            "efficiency_20", "volume_z", "vix_level", "vix_change_5", "weekday"]
QUANTILES = (.5, .8, .9)


def build():
    frame = load_history(DAILY, "^NDX")
    frame["date"] = pd.to_datetime(frame.date)
    frame = frame.sort_values("date").reset_index(drop=True)
    close, high, low = frame.close.astype(float), frame.high.astype(float), frame.low.astype(float)
    returns = close.pct_change()
    volatility = returns.rolling(20).std()
    true_range = pd.concat([high - low, (high - close.shift(1)).abs(),
                            (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = true_range.rolling(20).mean()
    data = pd.DataFrame({
        "date": frame.date,
        "ret_1_abs": returns.abs() / volatility,
        "ret_5_abs": (close / close.shift(5) - 1).abs() / (volatility * np.sqrt(5)),
        "vol_20": volatility / volatility.rolling(250).median(),
        "vol_ratio": volatility / volatility.rolling(250).mean(),
        "atr_pct": atr / close,
        "range_atr": (high - low) / atr,
        "efficiency_20": (close - close.shift(20)).abs() / close.diff().abs().rolling(20).sum(),
        "volume_z": (frame.volume - frame.volume.rolling(20).mean()) / frame.volume.rolling(20).std(),
        "weekday": frame.date.dt.dayofweek,
        "next_range_pct": (high.shift(-1) - low.shift(-1)) / close,
        "next_expansion": ((high.shift(-1) - low.shift(-1)) > 1.2 * atr).astype(float),
        "current_atr_pct": atr / close,
    })
    vix = load_history(DAILY, "^VIX").set_index("date").close
    vix.index = pd.to_datetime(vix.index)
    vix = vix.reindex(data.date).ffill().set_axis(data.index)
    data["vix_level"] = vix / vix.rolling(250).median()
    data["vix_change_5"] = vix.pct_change(5)
    return data


def final_holdout(data):
    """One-shot frozen evaluation. Configuration was fixed before this ran.

    Train through 2021, calibrate 2022-2023, test 2024 onward. Do not reuse this
    period for tuning; a second look invalidates it as a holdout.
    """
    embargo = pd.Timedelta(days=5)
    train = data[data.date < pd.Timestamp("2022-01-01") - embargo].dropna(subset=["next_range_pct"])
    cal = data[(data.date >= pd.Timestamp("2022-01-01")) &
               (data.date < pd.Timestamp("2024-01-01") - embargo)].dropna(subset=["next_range_pct"])
    test = data[data.date >= pd.Timestamp("2024-01-01")].dropna(subset=["next_range_pct"])
    predictions = {}
    for quantile in QUANTILES:
        model = make_pipeline(SimpleImputer(), LGBMRegressor(objective="quantile", alpha=quantile,
            n_estimators=150, num_leaves=15, learning_rate=.05, min_child_samples=50,
            random_state=7, n_jobs=1, verbosity=-1)).fit(train[FEATURES], train.next_range_pct)
        adjustment = np.quantile(cal.next_range_pct - model.predict(cal[FEATURES]), quantile)
        predictions[quantile] = model.predict(test[FEATURES]) + adjustment
    matrix = np.sort(np.maximum(np.column_stack([predictions[q] for q in QUANTILES]), 0), axis=1)
    actual = test.next_range_pct.to_numpy()
    result = {"train_rows": len(train), "calibration_rows": len(cal), "test_rows": len(test),
              "test_first": str(test.date.min().date()), "test_last": str(test.date.max().date()),
              "frozen_configuration": {"n_estimators": 150, "num_leaves": 15,
                                       "learning_rate": .05, "min_child_samples": 50, "seed": 7},
              "quantiles": {}}
    for j, quantile in enumerate(QUANTILES):
        baseline = float(np.quantile(train.next_range_pct, quantile))
        loss = np.maximum(quantile * (actual - matrix[:, j]), (quantile - 1) * (actual - matrix[:, j]))
        base_loss = np.maximum(quantile * (actual - baseline), (quantile - 1) * (actual - baseline))
        holdout = pd.DataFrame({"year": test.date.dt.year.to_numpy(), "actual": actual,
                                "predicted": matrix[:, j], "loss": loss})
        result["quantiles"][str(quantile)] = {
            "pinball_loss": float(loss.mean()), "baseline_loss": float(base_loss.mean()),
            "coverage": float((actual <= matrix[:, j]).mean()),
            "baseline_coverage": float((actual <= baseline).mean()),
            "by_year": {str(int(year)): {"n": len(block), "loss": float(block.loss.mean()),
                                         "coverage": float((block.actual <= block.predicted).mean())}
                        for year, block in holdout.groupby("year")},
            "paired_interval": block_mean_interval(loss - base_loss, test.date.dt.year.astype(str))}
    classifier = make_pipeline(SimpleImputer(), StandardScaler(),
                               LogisticRegression(C=.2, max_iter=2000)).fit(train[FEATURES], train.next_expansion)
    calibrated = PlattCalibrator().fit(
        classifier.predict_proba(cal[FEATURES])[:, 1], cal.next_expansion.to_numpy())
    probability = calibrated.predict(classifier.predict_proba(test[FEATURES])[:, 1])
    y = test.next_expansion.to_numpy()
    result["expansion"] = {**classification_metrics(y, probability),
                           "auc": float(roc_auc_score(y, probability)),
                           "baseline_brier": float(np.mean((float(train.next_expansion.mean()) - y) ** 2)),
                           "baseline_rate": float(train.next_expansion.mean())}
    return result


def main():
    data = build()
    years = sorted(y for y in data.date.dt.year.unique() if 1990 <= y < 2024)
    rows = []
    for year in years:
        cutoff = pd.Timestamp(f"{year - 2}-01-01")
        embargo = pd.Timedelta(days=5)
        train = data[(data.date < cutoff - embargo)].dropna(subset=["next_range_pct"])
        cal = data[(data.date >= cutoff) & (data.date < pd.Timestamp(f"{year}-01-01") - embargo)].dropna(subset=["next_range_pct"])
        test = data[(data.date >= pd.Timestamp(f"{year}-01-01")) & (data.date < pd.Timestamp(f"{year + 1}-01-01"))].dropna(subset=["next_range_pct"])
        if len(train) < 800 or len(cal) < 200 or len(test) < 100:
            continue
        predictions = {}
        for quantile in QUANTILES:
            model = make_pipeline(SimpleImputer(), LGBMRegressor(objective="quantile", alpha=quantile,
                n_estimators=150, num_leaves=15, learning_rate=.05, min_child_samples=50,
                random_state=7, n_jobs=1, verbosity=-1)).fit(train[FEATURES], train.next_range_pct)
            adjustment = np.quantile(cal.next_range_pct - model.predict(cal[FEATURES]), quantile)
            predictions[quantile] = model.predict(test[FEATURES]) + adjustment
        matrix = np.sort(np.maximum(np.column_stack([predictions[q] for q in QUANTILES]), 0), axis=1)
        for j, quantile in enumerate(QUANTILES):
            baseline = float(np.quantile(train.next_range_pct, quantile))
            actual = test.next_range_pct.to_numpy()
            loss = np.maximum(quantile * (actual - matrix[:, j]), (quantile - 1) * (actual - matrix[:, j]))
            base_loss = np.maximum(quantile * (actual - baseline), (quantile - 1) * (actual - baseline))
            rows.append(pd.DataFrame({"year": year, "date": test.date.to_numpy(), "quantile": quantile,
                                      "actual": actual, "predicted": matrix[:, j], "baseline": baseline,
                                      "loss": loss, "base_loss": base_loss,
                                      "covered": actual <= matrix[:, j],
                                      "baseline_covered": actual <= baseline}))
        # Expansion classifier, same fold.
        classifier = make_pipeline(SimpleImputer(), StandardScaler(),
                                   LogisticRegression(C=.2, max_iter=2000)).fit(train[FEATURES], train.next_expansion)
        calibrated = PlattCalibrator().fit(
            classifier.predict_proba(cal[FEATURES])[:, 1], cal.next_expansion.to_numpy())
        probability = calibrated.predict(classifier.predict_proba(test[FEATURES])[:, 1])
        rows.append(pd.DataFrame({"year": year, "date": test.date.to_numpy(), "quantile": "expansion",
                                  "actual": test.next_expansion.to_numpy(), "predicted": probability,
                                  "baseline": float(train.next_expansion.mean()),
                                  "loss": (probability - test.next_expansion) ** 2,
                                  "base_loss": (float(train.next_expansion.mean()) - test.next_expansion) ** 2,
                                  "covered": np.nan, "baseline_covered": np.nan}))
    frame = pd.concat(rows, ignore_index=True)
    report = {"decision": "NO_PROMOTION", "holdout_scored": False, "instrument": "^NDX",
              "reserved_from": 2024, "features": FEATURES,
              "walk_forward": {"type": "expanding annual", "calibration_years": 2, "embargo_days": 5},
              "results": {}}
    for quantile, group in frame.groupby("quantile"):
        entry = {"n": len(group),
                 "pinball_loss": float(group.loss.mean()),
                 "baseline_loss": float(group.base_loss.mean()),
                 "paired_interval": block_mean_interval((group.loss - group.base_loss).to_numpy(),
                                                        group.year.astype(str))}
        if quantile != "expansion":
            entry["coverage"] = float(group.covered.mean())
            entry["baseline_coverage"] = float(group.baseline_covered.mean())
            entry["median_predicted"] = float(group.predicted.median())
        else:
            y = group.actual.to_numpy()
            entry.update(classification_metrics(y, group.predicted.to_numpy()))
            entry["auc"] = float(roc_auc_score(y, group.predicted))
            entry["baseline_auc"] = 0.5
        entry["by_decade"] = {}
        for decade, block in group.groupby(group.year // 10 * 10):
            if quantile == "expansion":
                entry["by_decade"][str(int(decade))] = {
                    "n": len(block), "brier": float(block.loss.mean()),
                    "auc": float(roc_auc_score(block.actual, block.predicted)) if block.actual.nunique() == 2 else None}
            else:
                entry["by_decade"][str(int(decade))] = {
                    "n": len(block), "loss": float(block.loss.mean()),
                    "coverage": float(block.covered.mean())}
        report["results"][str(quantile)] = entry
        print(quantile, entry.get("pinball_loss", entry.get("brier")), entry.get("coverage"), entry.get("auc"))
    frame.to_csv(ROOT / "reports/phase3g_daily_range_predictions.csv", index=False)
    if "--final" in sys.argv:
        # Single frozen holdout evaluation. Running this again would contaminate it.
        report["final_holdout"] = final_holdout(data)
        print("FINAL", json.dumps({k: v for k, v in report["final_holdout"].items()
                                   if k in ("test_rows", "test_first", "test_last")}))
        print("FINAL quantiles", {k: (round(v["pinball_loss"], 6), round(v["coverage"], 4))
                                   for k, v in report["final_holdout"]["quantiles"].items()})
        print("FINAL expansion", report["final_holdout"]["expansion"])
    (ROOT / "reports/phase3g_daily_range.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
