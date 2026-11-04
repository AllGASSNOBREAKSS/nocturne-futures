"""Competing-outcome target research on development-only five-minute history."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from nocturne.adapters.history import checksum
from nocturne.backtest.data import add_session_column, load_intraday
from nocturne.backtest.study import build_dataset
from nocturne.instruments import get_instrument
from nocturne.ml.calibration import classification_metrics
from nocturne.ml.session_model import _align_classes, _calibrate
from nocturne.research.target_survival import (
    EVENT_NAMES, FEATURES, aalen_johansen, enrich_targets, event_rates, outcome_matrix,
)
from nocturne.research.validation import block_mean_interval, reserve_holdout, walk_forward
from nocturne.ml.session_model import _pipeline as _unused  # noqa: F401  (kept for parity imports)

ROOT = Path(__file__).resolve().parents[1]
DISTANCES = (50, 100, 150, 200, 350, 500)
HORIZON = 24
SLIPPAGE = 1


def model(kind):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if kind == "logistic":
        return make_pipeline(SimpleImputer(), StandardScaler(),
                             LogisticRegression(C=.5, max_iter=2000))
    from lightgbm import LGBMClassifier
    return make_pipeline(SimpleImputer(), LGBMClassifier(n_estimators=100, num_leaves=7,
        learning_rate=.05, min_child_samples=30, random_state=7, n_jobs=1, verbosity=-1))


def main():
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "event": f"fixed point target before original stop within {HORIZON} complete 5-minute bars",
              "protocol": "phase3f-survival-v1",
              "costs": {"slippage_ticks_per_side": SLIPPAGE, "commission_per_side": 2.5},
              "limitations": ["same-bar target+stop excluded as AMBIGUOUS",
                              "timeouts are censored, not stop losses",
                              "correlated targets from one signal stay in one fold",
                              "retrospective development only"], "strategies": {}}
    bars, meta = load_intraday("NQ")
    spec = get_instrument("NQ")
    bars = add_session_column(bars, spec)
    days = sorted(bars.session.unique())
    development_days = {str(d) for d in days[:int(.8 * len(days))]}
    frames = []
    for strategy in ("orb", "vwap", "value"):
        data, _ = build_dataset(strategy, "NQ", horizon_bars=HORIZON,
                                target_points=DISTANCES, slippage_ticks=SLIPPAGE)
        data["day"] = pd.to_datetime(data.feature_available_at, utc=True).dt.strftime("%Y-%m-%d")
        data = data[data.day.isin(development_days)].copy()
        data = enrich_targets(data, bars)
        data["distance_bucket"] = pd.cut(
            (data.target_price - data.entry_price).abs(),
            bins=[0, 100, 200, 350, 10000], labels=["50-100", "100-200", "200-350", "350-500+"])
        frames.append(data)
    data = pd.concat(frames, ignore_index=True)
    report["source"] = meta
    report["rows"] = len(data)
    report["signals"] = int(data.signal_id.nunique())
    report["days"] = int(data.day.nunique())
    report["date_range"] = [str(data.day.min()), str(data.day.max())]
    report["overall"] = event_rates(data)

    by_bucket = {}
    for bucket, group in data.groupby("distance_bucket", observed=True):
        entry = event_rates(group)
        entry["signals"] = int(group.signal_id.nunique())
        entry["median_target_atr"] = float(group.target_atr.median())
        entry["median_stop_atr"] = float(group.stop_atr.median())
        resolved = group[~group.ambiguous & ~group.censored]
        if len(resolved):
            entry["aalen_johansen"] = aalen_johansen(
                resolved.duration_bars.fillna(HORIZON), resolved.event, HORIZON)["incidence"]
            entry["aj_neither"] = aalen_johansen(
                resolved.duration_bars.fillna(HORIZON), resolved.event, HORIZON)["neither"]
        by_bucket[str(bucket)] = entry
    report["by_distance_bucket"] = by_bucket

    by_strategy = {}
    for strategy, group in data.groupby("strategy_id"):
        by_strategy[strategy] = event_rates(group)
    report["by_strategy"] = by_strategy

    # --- grouped purged validation -------------------------------------------
    prepared = data[~data.ambiguous & ~data.censored].copy()
    prepared["y"] = prepared.event.map({1: 0, 2: 1, 0: 2})  # target, stop, neither
    prepared["label_end"] = pd.to_datetime(prepared.label_end, utc=True)
    prepared["feature_available_at"] = pd.to_datetime(prepared.feature_available_at, utc=True)
    dev, holdout = reserve_holdout(prepared, group="day")
    folds = walk_forward(dev, min_train=10, calibration_groups=6, test_groups=4, group="day")
    report["folds"] = len(folds)
    report["quarantined_days"] = int(holdout.day.nunique())
    predictions = []
    for index, fold in enumerate(folds):
        train, cal, test = fold.train, fold.calibration, fold.test
        if train.y.nunique() < 3 or cal.y.nunique() < 3:
            continue
        y = test.y.to_numpy(dtype=int)
        frequency = train.y.value_counts(normalize=True).reindex([0, 1, 2], fill_value=0).to_numpy()
        rows = test[["signal_id", "day", "strategy_id", "distance_bucket", "y"]].copy()
        rows["fold"] = index
        rows[["p_target_freq", "p_stop_freq", "p_neither_freq"]] = np.tile(frequency, (len(test), 1))
        for kind in ("logistic", "lightgbm"):
            fitted = model(kind).fit(train[FEATURES], train.y)
            raw_cal = _align_classes(fitted, fitted.predict_proba(cal[FEATURES]))
            raw_test = _align_classes(fitted, fitted.predict_proba(test[FEATURES]))
            probability = _calibrate(raw_cal, cal.y.to_numpy(), raw_test)
            rows[[f"p_target_{kind}", f"p_stop_{kind}", f"p_neither_{kind}"]] = probability
        predictions.append(rows)
    if predictions:
        frame = pd.concat(predictions, ignore_index=True)
        summary = {}
        for kind in ("freq", "logistic", "lightgbm"):
            columns = [f"p_target_{kind}", f"p_stop_{kind}", f"p_neither_{kind}"]
            probability = frame[columns].to_numpy()
            onehot = np.eye(3)[frame.y.to_numpy()]
            loss = np.sum((probability - onehot) ** 2, axis=1)
            entry = {"n": len(frame), "brier": float(loss.mean()),
                     "log_loss": float(-np.mean(np.log(np.clip(
                         probability[np.arange(len(frame)), frame.y.to_numpy()], 1e-12, 1)))),
                     "class_counts": {EVENT_NAMES[k]: int(v) for k, v in
                                      frame.y.map({0: 1, 1: 2, 2: 0}).value_counts().items()},
                     "target_first": classification_metrics((frame.y == 0).astype(int).to_numpy(),
                                                           probability[:, 0]),
                     "stop_first": classification_metrics((frame.y == 1).astype(int).to_numpy(),
                                                          probability[:, 1]),
                     "brier_interval": block_mean_interval(loss, frame.day)}
            entry["target_first"]["auc"] = float(roc_auc_score((frame.y == 0).astype(int), probability[:, 0]))
            entry["stop_first"]["auc"] = float(roc_auc_score((frame.y == 1).astype(int), probability[:, 1]))
            summary[kind] = entry
        base = frame[["p_target_freq", "p_stop_freq", "p_neither_freq"]].to_numpy()
        base_loss = np.sum((base - np.eye(3)[frame.y.to_numpy()]) ** 2, axis=1)
        for kind in ("logistic", "lightgbm"):
            columns = [f"p_target_{kind}", f"p_stop_{kind}", f"p_neither_{kind}"]
            loss = np.sum((frame[columns].to_numpy() - np.eye(3)[frame.y.to_numpy()]) ** 2, axis=1)
            summary[kind]["paired_delta_vs_frequency"] = block_mean_interval(loss - base_loss, frame.day)
        report["validation"] = summary
        frame.to_csv(ROOT / "reports/phase3f_survival_predictions.csv", index=False)
    else:
        report["validation"] = {"status": "INSUFFICIENT_CLASSES"}

    data.to_csv(ROOT / "data/research/NQ_target_survival_phase3f.csv", index=False)
    report["dataset_sha256"] = checksum(ROOT / "data/research/NQ_target_survival_phase3f.csv")
    (ROOT / "reports/phase3f_survival.json").write_text(
        json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")
    print(json.dumps({"rows": report["rows"], "signals": report["signals"],
                      "overall": report["overall"],
                      "brier": {k: v.get("brier") for k, v in report["validation"].items()
                                if isinstance(v, dict)}}))


if __name__ == "__main__":
    main()
