"""Frozen-protocol retrospective walk-forward diagnostics; never scores holdout."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from nocturne.backtest.data import add_session_column, load_intraday
from nocturne.instruments import get_instrument
from nocturne.ml.session_model import evaluate_direction_split, multiclass_metrics
from nocturne.ml.target_model import evaluate_split
from nocturne.ml.calibration import classification_metrics
from nocturne.research.session_dataset import build_session_dataset, prepare_direction, prepare_consolidation
from nocturne.research.validation import reserve_holdout, walk_forward, block_mean_interval

ROOT = Path(__file__).resolve().parents[1]


def describe(frame):
    return {"n": len(frame), "days": frame.day.nunique(),
            "first": str(frame.feature_available_at.min()), "last": str(frame.feature_available_at.max()),
            "label_end": str(frame.label_end.max()),
            "classes": {str(k): int(v) for k, v in frame.y.value_counts().items()}}


def metrics(frame, task):
    if task == "direction":
        return multiclass_metrics(frame.y.to_numpy(), frame[["p0", "p1", "p2"]].to_numpy())
    result = classification_metrics(frame.y.to_numpy(), frame.p1.to_numpy())
    result["auc"] = float(roc_auc_score(frame.y, frame.p1)) if frame.y.nunique() == 2 else None
    return result


def run(data, task, rolling, feature_columns=None, min_train=12, calibration_groups=6, test_groups=4):
    if feature_columns is None:
        prepared, features = prepare_direction(data) if task == "direction" else prepare_consolidation(data)
    else:
        prepared, features = data.copy(), feature_columns
        prepared["y"] = prepared.direction.map({"BEAR": 0, "NEUTRAL": 1, "BULL": 2}) if task == "direction" else prepared.consolidation
    dev, holdout = reserve_holdout(prepared)
    folds = walk_forward(dev, min_train=min_train, calibration_groups=calibration_groups,
                         test_groups=test_groups, rolling_groups=rolling)
    predictions, partitions = [], []
    classes = 3 if task == "direction" else 2
    for index, fold in enumerate(folds):
        train, calibration, test = fold.train, fold.calibration, fold.test
        partitions.append({"fold": index, "train": describe(train), "calibration": describe(calibration),
                           "test": describe(test)})
        if train.y.nunique() < 2:
            partitions[-1]["status"] = "INSUFFICIENT_CLASSES"
            continue
        evaluator = evaluate_direction_split if task == "direction" else evaluate_split
        results = evaluator(train, calibration, test, features)
        partitions[-1]["models"] = {name: result.metrics for name, result in results.items()}
        probabilities = {}
        for name, result in results.items():
            pred = result.predictions
            probabilities[name] = (pred[["p_bear", "p_neutral", "p_bull"]].to_numpy()
                                   if task == "direction" else np.c_[1 - pred.p, pred.p])
        # Genuine current-state persistence and train-only transition smoothing.
        column = "persistence_direction" if task == "direction" else "persistence_consolidation"
        mapping = {"BEAR": 0, "NEUTRAL": 1, "BULL": 2}
        states = test[column].map(mapping) if task == "direction" else test[column]
        prior = np.bincount(train.y.astype(int), minlength=classes) + 1
        prior = prior / prior.sum()
        hard, transition = [], []
        for value in states:
            if pd.isna(value):
                hard.append(prior)
                transition.append(prior)
                continue
            state = int(value)
            hard.append(np.eye(classes)[state])
            train_states = train[column].map(mapping) if task == "direction" else train[column]
            labels = train.loc[train_states == state, "y"].astype(int)
            counts = np.bincount(labels, minlength=classes) + 1
            transition.append(counts / counts.sum())
        probabilities["persistence"] = np.asarray(hard)
        probabilities["historical_transition"] = np.asarray(transition)
        baseline_loss = None
        for name, probs in probabilities.items():
            y = test.y.to_numpy(dtype=int)
            loss = np.sum((probs - np.eye(classes)[y]) ** 2, axis=1)
            if task != "direction":
                loss /= 2
            if name == "frequency":
                baseline_loss = loss
            rows = test[["signal_id", "day", "session", "y", "efficiency"]].copy()
            rows["state_stratum"] = np.where(rows.efficiency >= 0.3, "efficient", "low_efficiency")
            rows["model"], rows["fold"] = name, index
            for c in range(classes):
                rows[f"p{c}"] = probs[:, c]
            rows["brier_loss"] = loss
            rows["paired_brier_delta"] = loss - baseline_loss
            predictions.append(rows)
    if not predictions:
        return {"status": "INSUFFICIENT_DATA", "partitions": partitions}, pd.DataFrame()
    predictions = pd.concat(predictions, ignore_index=True)
    summary = {}
    for model, rows in predictions.groupby("model"):
        summary[model] = {"metrics": metrics(rows, task),
                          "brier_interval": block_mean_interval(rows.brier_loss, rows.day),
                          "paired_delta_interval": block_mean_interval(rows.paired_brier_delta, rows.day),
                          "sessions": {s: metrics(g, task) for s, g in rows.groupby("session")},
                          "strata": {s: metrics(g, task) for s, g in rows.groupby("state_stratum")}}
    return {"status": "RETROSPECTIVE_ONLY", "partitions": partitions,
            "development": describe(dev), "quarantined_days": holdout.day.nunique(),
            "holdout_scored": False, "summary": summary}, predictions


def main():
    nq, nq_meta = load_intraday("NQ")
    es, es_meta = load_intraday("ES")
    spec, es_spec = get_instrument("NQ"), get_instrument("ES")
    vix = pd.read_csv(ROOT / "data/market/daily/VIX.csv")
    vix["date"] = pd.to_datetime(vix.date).dt.strftime("%Y-%m-%d")
    data = build_session_dataset(add_session_column(nq, spec), add_session_column(es, es_spec),
                                 vix, spec, es_spec=es_spec)
    path = ROOT / "data/research/session_dataset_NQ_phase3d.csv"
    data.to_csv(path, index=False)
    report = {"decision": "NO_PROMOTION", "independent_final_holdout": "DATA_BLOCKED",
              "protocol_sha256": hashlib.sha256((ROOT / "docs/PHASE3D_PROTOCOL.md").read_bytes()).hexdigest(),
              "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "sources": {"NQ": nq_meta, "ES": es_meta}, "rows": len(data),
              "days": data.day.nunique(), "experiments": {}}
    for task in ("direction", "consolidation"):
        for rolling in (None, 12):
            key = task + ("_rolling" if rolling else "_expanding")
            result, predictions = run(data, task, rolling)
            report["experiments"][key] = result
            predictions.to_csv(ROOT / f"reports/phase3d_{key}_predictions.csv", index=False)
    # Fixed label comparisons describe development only, never the quarantine.
    prepared, _ = prepare_direction(data)
    dev, _ = reserve_holdout(prepared)
    report["label_comparison_development"] = {
        "original_direction": dev.direction.value_counts().to_dict(),
        "scaled_direction": dev.scaled_direction.value_counts().to_dict(),
        "duration_consolidation_disagreements": int((dev.consolidation != dev.duration_consolidation).sum()),
        "session_minutes": dev.groupby("session").current_minutes.unique().apply(list).to_dict()}
    output = ROOT / "reports/phase3d_validation.json"
    output.write_text(json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")
    print(json.dumps({"rows": len(data), "days": data.day.nunique(), "decision": "NO_PROMOTION"}))
    for key, result in report["experiments"].items():
        print(key, {name: item["metrics"]["brier"] for name, item in result.get("summary", {}).items()})


if __name__ == "__main__":
    main()
