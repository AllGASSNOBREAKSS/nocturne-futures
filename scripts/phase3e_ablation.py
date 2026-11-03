"""Fixed logistic/LightGBM feature ablations; never scores final 20% days."""
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from nocturne.adapters.history import checksum
from nocturne.ml.session_model import _align_classes, _calibrate, multiclass_metrics
from nocturne.ml.calibration import PlattCalibrator, classification_metrics
from nocturne.research.hourly_dataset import FEATURES
from nocturne.research.validation import reserve_holdout, walk_forward, block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {"momentum": ["momentum_2", "momentum_6", "efficiency"],
          "volume": ["volume_ratio", "zero_volume_context"],
          "clock": ["hour_sin", "hour_cos"],
          "volatility": ["atr_pct", "realized_vol", "range_atr"]}


def factory(name):
    if name == "logistic":
        return make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(C=.5, max_iter=1000))
    from lightgbm import LGBMClassifier
    return make_pipeline(SimpleImputer(), LGBMClassifier(n_estimators=100, num_leaves=7,
        learning_rate=.05, min_child_samples=50, random_state=7, n_jobs=1, verbosity=-1))


def main():
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "protocol_sha256": checksum(ROOT / "docs/PHASE3E_PROTOCOL.md"),
              "lightgbm_version": importlib.metadata.version("lightgbm"), "experiments": {}}
    all_predictions = []
    for instrument in ("NQ", "ES"):
        source = ROOT / f"data/research/{instrument}_two_hour_phase3d.csv"
        data = pd.read_csv(source)
        for task in ("direction", "consolidation"):
            data["y"] = data.direction.map({"BEAR": 0, "NEUTRAL": 1, "BULL": 2}) if task == "direction" else data.consolidation
            dev, _ = reserve_holdout(data)
            folds = walk_forward(dev, min_train=60, calibration_groups=20, test_groups=30)
            k = 3 if task == "direction" else 2
            parts = []
            for fold_id, fold in enumerate(folds):
                train, calibration, test = fold.train, fold.calibration, fold.test
                y = test.y.to_numpy(dtype=int)
                freq = train.y.value_counts(normalize=True).reindex(range(k), fill_value=0).to_numpy()
                baseline = np.sum((freq - np.eye(k)[y]) ** 2, axis=1) / (1 if k == 3 else 2)
                for model_name in ("logistic", "lightgbm"):
                    for omitted in ("none", *GROUPS):
                        features = [x for x in FEATURES if x not in GROUPS.get(omitted, [])]
                        model = factory(model_name).fit(train[features], train.y)
                        raw = model.predict_proba(test[features])
                        cal = model.predict_proba(calibration[features])
                        if k == 3:
                            raw, cal = _align_classes(model, raw), _align_classes(model, cal)
                            p = _calibrate(cal, calibration.y.to_numpy(), raw)
                        else:
                            p1 = PlattCalibrator().fit(cal[:, 1], calibration.y.to_numpy()).predict(raw[:, 1]) if calibration.y.nunique() == 2 else raw[:, 1]
                            p = np.c_[1-p1, p1]
                        rows = test[["signal_id", "day", "y", "feature_available_at"]].copy()
                        rows["instrument"], rows["task"], rows["model"], rows["omitted"] = instrument, task, model_name, omitted
                        rows["fold"] = fold_id
                        for c in range(k):
                            rows[f"p{c}"] = p[:, c]
                        rows["brier_loss"] = np.sum((p - np.eye(k)[y]) ** 2, axis=1) / (1 if k == 3 else 2)
                        rows["delta_frequency"] = rows.brier_loss - baseline
                        parts.append(rows)
            predictions = pd.concat(parts, ignore_index=True)
            all_predictions.append(predictions)
            summary = {}
            for (model, omitted), rows in predictions.groupby(["model", "omitted"]):
                metrics = (multiclass_metrics(rows.y.to_numpy(), rows[["p0", "p1", "p2"]].to_numpy()) if k == 3
                           else classification_metrics(rows.y.to_numpy(), rows.p1.to_numpy()))
                if k == 2:
                    metrics["auc"] = float(roc_auc_score(rows.y, rows.p1))
                full = predictions[(predictions.model == model) & (predictions.omitted == "none")].set_index("signal_id")
                aligned = full.loc[rows.signal_id, "brier_loss"].to_numpy()
                summary[f"{model}_without_{omitted}"] = {"metrics": metrics,
                    "classes": rows.y.value_counts().to_dict(),
                    "first": str(rows.feature_available_at.min()), "last": str(rows.feature_available_at.max()),
                    "delta_frequency": block_mean_interval(rows.delta_frequency, rows.day),
                    "delta_full": block_mean_interval(rows.brier_loss.to_numpy() - aligned, rows.day)}
            report["experiments"][f"{instrument}_{task}"] = {"source_sha256": checksum(source),
                "folds": [{"train_n": len(f.train), "calibration_n": len(f.calibration), "test_n": len(f.test),
                           "train_label_end": str(f.train.label_end.max()),
                           "calibration_first": str(f.calibration.feature_available_at.min()),
                           "calibration_label_end": str(f.calibration.label_end.max()),
                           "test_first": str(f.test.feature_available_at.min())} for f in folds], "summary": summary}
            print(instrument, task, {key: value["metrics"]["brier"] for key, value in summary.items()})
    pd.concat(all_predictions, ignore_index=True).to_csv(ROOT / "reports/phase3e_ablation_predictions.csv.gz", index=False,
                                                        compression={"method": "gzip", "mtime": 0})
    (ROOT / "reports/phase3e_ablation.json").write_text(json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")


if __name__ == "__main__":
    main()
