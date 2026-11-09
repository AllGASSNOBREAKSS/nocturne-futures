"""Studio training jobs: configurable walk-forward research models.

Daily NQ/ES continuous-proxy sessions (roll windows excluded) with the
Phase 3U point-in-time feature join. Annual expanding or windowed refits,
embargo, a separate calibration slice, a trailing-frequency baseline and an
explicit holdout era. Models are research-only; nothing is promoted.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..research import futures_free as ff
from ..research.free_data_experiment import block_bootstrap, direction_metrics
from . import ROOT, atomic_write, market

FAMILIES = {"price": ff.PRICE, **ff.FAMILIES}
MODELS = ("frequency", "logistic", "random_forest", "lightgbm")
OBJECTIVES = ("direction", "compression", "range_ge_points", "range_quantile")
ROLLS = ROOT / "data/history/free/rolls/front_month_volume_rolls.json"


def validate(c):
    e = []
    if c.get("root") not in market.ROOTS:
        e.append("instrument must be NQ or ES")
    if c.get("objective") not in OBJECTIVES:
        e.append("unknown objective")
    if c.get("model") not in MODELS:
        e.append("unknown model family")
    if c.get("objective") == "range_quantile" and c.get("model") not in ("frequency", "lightgbm"):
        e.append("range quantiles support frequency baseline or LightGBM")
    if c.get("objective") == "range_ge_points" and not 1 <= float(c.get("threshold_points", 0)) <= 5000:
        e.append("threshold_points must be 1-5000")
    fams = c.get("feature_families") or ["price"]
    if any(f not in FAMILIES for f in fams):
        e.append("unknown feature family")
    first, last, hold = int(c.get("first_test_year", 2008)), int(c.get("last_test_year", 2026)), int(c.get("holdout_from", 2024))
    if not 2003 <= first <= last <= 2026 or not first < hold <= last + 1:
        e.append("test years must satisfy 2003 <= first < holdout_from <= last+1, last <= 2026")
    if c.get("training_window_years") not in (None, 3, 5, 10, 15, 20):
        e.append("training window must be expanding or 3/5/10/15/20 years")
    if not 0 <= int(c.get("embargo_days", 5)) <= 60 or not 100 <= int(c.get("calibration_rows", 250)) <= 1000:
        e.append("embargo 0-60 days, calibration 100-1000 rows")
    return e


def _dataset(root, threshold=None):
    rolls = sorted(pd.Timestamp(d).date() for d in json.loads(ROLLS.read_text())[f"{root}.v.0"]["dates"])
    saved = ff.PROTOCOL["large_move_points"]
    # Baselines are built on the full series before roll windows are removed (as in Phase 3V).
    ff.PROTOCOL["large_move_points"] = [threshold] if threshold else []
    try:
        data, audit, near = ff.daily_frame(market.archive(), root, rolls)
    finally:
        ff.PROTOCOL["large_move_points"] = saved
    return data, {"rolls": len(rolls), "excluded_near_roll": near, "pit_audit": audit}


def _model(c):
    kind = c["model"]
    seed = 7
    if kind == "logistic":
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        return make_pipeline(StandardScaler(), LogisticRegression(C=float(c.get("C", 0.2)), max_iter=2000))
    if kind == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=int(c.get("n_estimators", 300)), max_depth=int(c.get("max_depth", 6)),
                                      min_samples_leaf=50, random_state=seed, n_jobs=1)
    from lightgbm import LGBMClassifier
    return LGBMClassifier(n_estimators=int(c.get("n_estimators", 200)), learning_rate=float(c.get("learning_rate", 0.03)),
                          num_leaves=int(c.get("num_leaves", 15)), min_child_samples=50, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.8, random_state=seed, verbose=-1)


def _importance(model, features):
    est = model.steps[-1][1] if hasattr(model, "steps") else model
    values = getattr(est, "feature_importances_", None)
    if values is None and hasattr(est, "coef_"):
        values = np.abs(est.coef_[0])
    if values is None:
        return []
    total = float(np.sum(values)) or 1.0
    return sorted(({"feature": f, "importance": round(float(v) / total, 5)} for f, v in zip(features, values)), key=lambda x: -x["importance"])


def reliability(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    return [{"bin": f"{edges[b]:.1f}-{edges[b + 1]:.1f}", "n": int((idx == b).sum()),
             "mean_predicted": round(float(p[idx == b].mean()), 4), "observed": round(float(y[idx == b].mean()), 4)}
            for b in range(bins) if (idx == b).any()]


def run(c, directory, progress=lambda pct, msg: None, cancelled=lambda: False):
    errors = validate(c)
    if errors:
        return {"status": "BLOCKED", "reason": "INVALID_CONFIGURATION", "errors": errors}
    directory = Path(directory)
    threshold = float(c["threshold_points"]) if c["objective"] == "range_ge_points" else None
    if threshold is not None and threshold.is_integer():
        threshold = int(threshold)
    data, provenance = _dataset(c["root"], threshold)
    progress(5, f"{len(data)} sessions after roll exclusion")
    features = sorted({f for fam in (c.get("feature_families") or ["price"]) for f in FAMILIES[fam]}, key=lambda x: (x not in ff.PRICE, x))
    objective = c["objective"]
    if objective == "direction":
        label, base = "next_up", "base_up"
    elif objective == "compression":
        label, base = "y_compress", "base_compress"
    elif objective == "range_ge_points":
        label, base = f"y_range_{threshold}", f"base_range_{threshold}"
    else:
        label, base = "next_range", None
    usable = data.dropna(subset=features + [label] + ([base] if base else []))
    years = list(range(int(c.get("first_test_year", 2008)), int(c.get("last_test_year", 2026)) + 1))
    holdout = int(c.get("holdout_from", 2024))
    window = c.get("training_window_years")
    rows, folds, model = [], [], None
    for k, year in enumerate(years):
        if cancelled():
            from .backtest import Cancelled
            raise Cancelled()
        test = usable[usable.year == year]
        train = usable[pd.to_datetime(usable.date) < pd.Timestamp(f"{year}-01-01") - pd.Timedelta(days=int(c.get("embargo_days", 5)))]
        if window:
            train = train[pd.to_datetime(train.date) >= pd.Timestamp(f"{year - int(window)}-01-01")]
        if test.empty or len(train) < 750:  # same minimum as Phase 3V research
            folds.append({"year": year, "status": "SKIPPED_INSUFFICIENT_TRAINING"})
            continue
        frame = pd.DataFrame({"date": test.date.to_numpy(), "year": year, "y": test[label].to_numpy()})
        if objective == "range_quantile":
            trail = data.range_pts.rolling(250)
            for q in (0.5, 0.8, 0.9):
                frame[f"base_q{int(q * 100)}"] = trail.quantile(q).reindex(test.index).to_numpy()
                if c["model"] == "lightgbm":
                    from lightgbm import LGBMRegressor
                    reg = LGBMRegressor(objective="quantile", alpha=q, n_estimators=int(c.get("n_estimators", 300)),
                                        learning_rate=float(c.get("learning_rate", 0.03)), num_leaves=int(c.get("num_leaves", 15)),
                                        min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=7, verbose=-1)
                    reg.fit(train[features], train[label])
                    frame[f"q{int(q * 100)}"] = reg.predict(test[features])
                    model = reg
                else:
                    frame[f"q{int(q * 100)}"] = frame[f"base_q{int(q * 100)}"]
        else:
            cal_n = int(c.get("calibration_rows", 250))
            fit, cal = train.iloc[:-cal_n], train.iloc[-cal_n:]
            frame["p_base"] = test[base].clip(1e-4, 1 - 1e-4).to_numpy()
            if c["model"] == "frequency" or fit[label].nunique() < 2 or cal[label].nunique() < 2:
                frame["p_model"] = float(train[label].mean()) if c["model"] == "frequency" else np.nan
            else:
                from ..ml.calibration import PlattCalibrator
                model = _model(c)
                model.fit(fit[features], fit[label])
                platt = PlattCalibrator().fit(model.predict_proba(cal[features])[:, 1], cal[label].to_numpy())
                frame["p_model"] = platt.predict(model.predict_proba(test[features])[:, 1])
        frame["era"] = np.where(year >= holdout, "holdout", "development")
        rows.append(frame.dropna())
        folds.append({"year": year, "train_rows": len(train), "test_rows": len(test), "train_start": str(train.date.min()), "train_end": str(train.date.max())})
        progress(10 + int(75 * (k + 1) / len(years)), f"fold {year}: train {len(train)}, test {len(test)}")
    if not rows:
        return {"status": "BLOCKED", "reason": "NO_ELIGIBLE_FOLDS"}
    pred = pd.concat(rows, ignore_index=True)
    pred.to_csv(directory / "predictions.csv", index=False, lineterminator="\n")
    report = {"config": c, "features": features, "dataset": provenance, "folds": folds, "objective": objective,
              "sessions_scored": len(pred), "metrics": {}, "by_year": {}, "scope": "RETROSPECTIVE_WALK_FORWARD_CONTINUOUS_PROXY"}
    for era in ("development", "holdout"):
        f = pred[pred.era == era].reset_index(drop=True)
        if f.empty:
            continue
        if objective == "range_quantile":
            m = {}
            for name in ("model", "baseline"):
                cols = {q: (f"q{q}" if name == "model" else f"base_q{q}") for q in (50, 80, 90)}
                losses = [np.maximum(q / 100 * (f.y - f[col]), (q / 100 - 1) * (f.y - f[col])) for q, col in cols.items()]
                m[name] = {**{f"coverage_q{q}": round(float((f.y <= f[col]).mean()), 4) for q, col in cols.items()},
                           "mean_pinball": round(float(np.mean(losses)), 4)}
            mp = lambda prefix: np.mean([np.maximum(q / 100 * (f.y - f[f"{prefix}{q}"]), (q / 100 - 1) * (f.y - f[f"{prefix}{q}"])) for q in (50, 80, 90)], axis=0)
            m["pinball_model_minus_baseline"] = block_bootstrap(f, mp("q"), mp("base_q"), 1000, 7)
        else:
            y = f.y.to_numpy()
            m = {"model": direction_metrics(y, f.p_model), "baseline": direction_metrics(y, f.p_base),
                 "brier_model_minus_baseline": block_bootstrap(f, (f.p_model - y) ** 2, (f.p_base - y) ** 2, 1000, 7),
                 "reliability": reliability(y, f.p_model.to_numpy())}
        report["metrics"][era] = m
    for year, f in pred.groupby("year"):
        if objective == "range_quantile":
            report["by_year"][str(year)] = {"n": len(f), "coverage_q80": round(float((f.y <= f.q80).mean()), 4),
                                            "baseline_coverage_q80": round(float((f.y <= f.base_q80).mean()), 4)}
        else:
            y = f.y.to_numpy()
            report["by_year"][str(year)] = {"n": len(f), "brier_model": round(float(np.mean((f.p_model - y) ** 2)), 5),
                                            "brier_baseline": round(float(np.mean((f.p_base - y) ** 2)), 5)}
    key = "pinball_model_minus_baseline" if objective == "range_quantile" else "brier_model_minus_baseline"
    dev, hold = report["metrics"].get("development", {}).get(key), report["metrics"].get("holdout", {}).get(key)
    report["verdict"] = ("REJECT" if dev and dev["ci95"][0] > 0 else
                         "ACCEPT_RESEARCH_ONLY" if dev and hold and dev["ci95"][1] < 0 and hold["mean"] < 0 else "INCONCLUSIVE")
    if model is not None and c["model"] != "frequency":
        import joblib
        joblib.dump({"model": model, "features": features, "config": c}, directory / "model.joblib")
        report["artifact_sha256"] = hashlib.sha256((directory / "model.joblib").read_bytes()).hexdigest()
        report["feature_importance"] = _importance(model, features)
    report["promotion"], report["trading_decision"] = "NO_PROMOTION", "NO_TRADE"
    atomic_write(directory / "report.json", json.dumps(report, indent=2, default=str))
    progress(100, "done")
    return {"status": "SUCCEEDED", "verdict": report["verdict"], "sessions_scored": len(pred), "report_path": str(directory / "report.json"),
            "headline": {era: (v.get(key) or {}).get("mean") for era, v in report["metrics"].items()}}
