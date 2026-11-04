"""Phase 3F direction diagnostics and hierarchical formulation.

Development folds only (last 20% of days unscored). Labels are unchanged; the
diagnostic columns (close/ATR/threshold) are additive and must not feed models.
"""
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
from nocturne.ml.calibration import PlattCalibrator, classification_metrics, expected_calibration_error
from nocturne.ml.session_model import _align_classes, _calibrate, multiclass_metrics
from nocturne.research.hourly_dataset import FEATURES
from nocturne.research.validation import reserve_holdout, walk_forward, block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
# Additive diagnostic columns must never become model inputs.
assert not set(["close", "atr_points", "threshold_points", "move_points", "move_atr"]) & set(FEATURES)


def model(name, seed=7):
    if name == "logistic":
        return make_pipeline(SimpleImputer(), StandardScaler(),
                             LogisticRegression(C=.5, max_iter=1000, random_state=seed))
    from lightgbm import LGBMClassifier
    return make_pipeline(SimpleImputer(), LGBMClassifier(n_estimators=100, num_leaves=7,
        learning_rate=.05, min_child_samples=50, random_state=seed, n_jobs=1, verbosity=-1))


def multinomial_calibrator(raw_cal, y_cal, raw_test):
    """Vector scaling: one temperature-like slope per class on logits."""
    raw_cal = np.clip(raw_cal, 1e-6, 1 - 1e-6)
    raw_test = np.clip(raw_test, 1e-6, 1 - 1e-6)
    z_cal, z_test = np.log(raw_cal), np.log(raw_test)
    calibrator = LogisticRegression(C=1e6, max_iter=2000)
    calibrator.fit(z_cal, y_cal)
    return _align_classes(calibrator, calibrator.predict_proba(z_test))


def abstention(probabilities, threshold):
    confidence = probabilities.max(axis=1)
    keep = confidence >= threshold
    return keep, float(keep.mean())


def main():
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "protocol": "phase3f-direction-diagnostics-v1",
              "lightgbm_version": importlib.metadata.version("lightgbm"),
              "instruments": {}}
    for instrument in ("NQ", "ES"):
        source = ROOT / f"data/research/{instrument}_two_hour_phase3f.csv"
        data = pd.read_csv(source)
        y3 = data.direction.map({"BEAR": 0, "NEUTRAL": 1, "BULL": 2}).to_numpy()
        material = (data.direction != "NEUTRAL").to_numpy()
        bull = (data.direction == "BULL").to_numpy()
        data["y"] = y3
        dev, _ = reserve_holdout(data)
        folds = walk_forward(dev, min_train=60, calibration_groups=20, test_groups=30)
        parts = []
        for fold_id, fold in enumerate(folds):
            train, cal, test = fold.train, fold.calibration, fold.test
            test_index = test.index
            parts.append({"fold": fold_id, "test": test, "train": train, "cal": cal})        # --- label threshold audit on development rows only -------------------
        ratio = (dev.move_points.abs() / dev.threshold_points)
        stamp = pd.to_datetime(dev.feature_available_at, utc=True)
        audit = {"rows": len(dev), "neutral_share": float((dev.direction == "NEUTRAL").mean()),
                 "abs_move_over_threshold": {str(q): float(ratio.quantile(q)) for q in (.5, .64, .75, .9, .95)},
                 "threshold_definition": "0.5 * ATR(24 hourly true ranges) * sqrt(2)",
                 "neutral_band_is_wide": bool(ratio.quantile(.64) > 1.5),
                 "by_hour_utc": {str(int(h)): {"n": int(len(g)),
                                               "neutral": float((g.direction == "NEUTRAL").mean()),
                                               "bull": float((g.direction == "BULL").mean())}
                                 for h, g in dev.groupby(stamp.dt.hour)},
                 "monthly_neutral": {m: float((g.direction == "NEUTRAL").mean())
                                     for m, g in dev.groupby(dev.day.str[:7])}}
        report["instruments"][instrument] = {"source_sha256": checksum(source), "label_audit": audit}

        # --- model comparison across folds -----------------------------------
        collected = {"three_class": [], "hierarchical": [], "hierarchical_calibrated": [],
                     "two_stage_neutral": []}
        for item in parts:
            train, cal, test = item["train"], item["cal"], item["test"]
            for name in ("logistic", "lightgbm"):
                model3 = model(name).fit(train[FEATURES], train.y)
                raw_cal = _align_classes(model3, model3.predict_proba(cal[FEATURES]))
                raw_test = _align_classes(model3, model3.predict_proba(test[FEATURES]))
                p3 = _calibrate(raw_cal, cal.y.to_numpy(), raw_test)
                p3v = multinomial_calibrator(raw_cal, cal.y.to_numpy(), raw_test)
                stage_a_train = (train.y != 1).astype(int)
                stage_b_train = (train.y == 2).astype(int)
                a = model(name).fit(train[FEATURES], stage_a_train)
                b = model(name).fit(train[train.y != 1][FEATURES], stage_b_train[train.y.to_numpy() != 1])
                pa_cal = PlattCalibrator().fit(a.predict_proba(cal[FEATURES])[:, 1], (cal.y != 1).astype(int).to_numpy())
                pb_cal = PlattCalibrator().fit(b.predict_proba(cal[cal.y != 1][FEATURES])[:, 1],
                                               (cal.y[cal.y != 1] == 2).astype(int).to_numpy())
                pa = pa_cal.predict(a.predict_proba(test[FEATURES])[:, 1])
                pb = pb_cal.predict(b.predict_proba(test[FEATURES])[:, 1])
                phier = np.c_[np.clip((1 - pa) * (1 - pb), 0, 1), 1 - pa, np.clip((1 - pa) * pb, 0, 1)]
                phier /= phier.sum(axis=1, keepdims=True)
                rows = test[["signal_id", "day", "y"]].copy()
                rows["fold"], rows["model"] = item["fold"], name
                rows["p_bear_3"], rows["p_neutral_3"], rows["p_bull_3"] = p3.T
                rows["p_bear_v"], rows["p_neutral_v"], rows["p_bull_v"] = p3v.T
                rows["p_material"], rows["p_bull_given"] = pa, pb
                rows["p_bear_h"], rows["p_neutral_h"], rows["p_bull_h"] = phier.T
                collected["three_class"].append(rows)
                collected["hierarchical"].append(rows)
        frame = pd.concat(collected["three_class"], ignore_index=True)

        def metrics_from(columns):
            p = frame[columns].to_numpy()
            m = multiclass_metrics(frame.y.to_numpy(), p)
            p_material = 1 - p[:, 1]
            material_y = (frame.y != 1).astype(int)
            m["material"] = classification_metrics(material_y.to_numpy(), p_material)
            m["material"]["auc"] = float(roc_auc_score(material_y, p_material))
            conditional = frame[frame.y != 1]
            p_cond = conditional[columns[2]].to_numpy()
            m["bull_given_material"] = classification_metrics((conditional.y == 2).astype(int).to_numpy(), p_cond)
            m["bull_given_material"]["auc"] = float(roc_auc_score((conditional.y == 2).astype(int), p_cond))
            return m

        per_model = {}
        for name in ("logistic", "lightgbm"):
            g = frame[frame.model == name]
            for variant, cols in (("three_class_raw_calibrated", ["p_bear_3", "p_neutral_3", "p_bull_3"]),
                                  ("three_class_vector_scaled", ["p_bear_v", "p_neutral_v", "p_bull_v"]),
                                  ("hierarchical", ["p_bear_h", "p_neutral_h", "p_bull_h"])):
                p = g[cols].to_numpy()
                m = multiclass_metrics(g.y.to_numpy(), p)
                material_y = (g.y != 1).astype(int).to_numpy()
                m["material"] = classification_metrics(material_y, 1 - p[:, 1])
                m["material"]["auc"] = float(roc_auc_score(material_y, 1 - p[:, 1]))
                cond = g[g.y != 1]
                m["bull_given_material"] = classification_metrics((cond.y == 2).astype(int).to_numpy(), cond[cols[2]])
                m["bull_given_material"]["auc"] = float(roc_auc_score((cond.y == 2).astype(int), cond[cols[2]]))
                per_model[f"{name}_{variant}"] = m
            # abstention trade-off: accuracy on kept rows vs coverage
            p = g[["p_bear_3", "p_neutral_3", "p_bull_3"]].to_numpy()
            per_model[f"{name}_abstention"] = {}
            for threshold in (.4, .5, .6, .7, .8):
                keep = p.max(axis=1) >= threshold
                if keep.sum() == 0:
                    per_model[f"{name}_abstention"][str(threshold)] = {"coverage": 0.0, "accuracy": None}
                    continue
                pred = p[keep].argmax(axis=1)
                per_model[f"{name}_abstention"][str(threshold)] = {
                    "coverage": round(float(keep.mean()), 4),
                    "accuracy": round(float((pred == g.y.to_numpy()[keep]).mean()), 4),
                    "n": int(keep.sum())}
        report["instruments"][instrument]["models"] = per_model

        # --- probability distribution and per-class precision ---------------
        g = frame[frame.model == "lightgbm"]
        p = g[["p_bear_3", "p_neutral_3", "p_bull_3"]].to_numpy()
        report["instruments"][instrument]["lightgbm_diagnostics"] = {
            "class_counts": {int(k): int(v) for k, v in g.y.value_counts().items()},
            "predicted_counts": {int(k): int(v) for k, v in pd.Series(p.argmax(axis=1)).value_counts().items()},
            "mean_probability_by_true_class": {
                str(c): {"bear": float(p[g.y == c, 0].mean()), "neutral": float(p[g.y == c, 1].mean()),
                         "bull": float(p[g.y == c, 2].mean())} for c in (0, 1, 2)},
            "precision_per_class": {
                str(c): float((g.y.to_numpy()[p.argmax(axis=1) == c] == c).mean())
                if (p.argmax(axis=1) == c).any() else None for c in (0, 1, 2)},
            "brier_interval": block_mean_interval(np.sum((p - np.eye(3)[g.y.to_numpy()]) ** 2, axis=1), g.day)}
        frame.to_csv(ROOT / f"reports/phase3f_{instrument}_direction_predictions.csv.gz", index=False,
                     compression={"method": "gzip", "mtime": 0})
        print(instrument, {k: round(v["brier"], 4) for k, v in per_model.items() if "brier" in v})
    (ROOT / "reports/phase3f_direction.json").write_text(
        json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")


if __name__ == "__main__":
    main()
