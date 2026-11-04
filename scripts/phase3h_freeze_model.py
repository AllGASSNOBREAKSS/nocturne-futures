"""Freeze the validated NDX daily-range model and verify holdout reproduction.

The configuration and data cutoffs are identical to the Phase 3G one-shot
evaluation. The script refuses to save an artifact that does not reproduce the
stored holdout metrics.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from nocturne.adapters.yahoo_history import load_history
from nocturne.shadow.features import FEATURES, build_history
from nocturne.shadow.model import save_artifact

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"
MODEL_ID = "ndx-range-v1"
VERSION = "1.0.0"
QUANTILES = {"p50": 0.5, "p80": 0.8, "p90": 0.9}
CONFIG = {"n_estimators": 150, "num_leaves": 15, "learning_rate": 0.05,
          "min_child_samples": 50, "random_state": 7, "n_jobs": 1}
TRAIN_END = "2022-01-01"
CAL_START = "2022-01-01"
CAL_END = "2024-01-01"
HOLDOUT_START = "2024-01-01"


def main():
    index = load_history(DAILY, "^NDX")
    vix = load_history(DAILY, "^VIX")
    data = build_history(index, vix)
    embargo = pd.Timedelta(days=5)
    train = data[data.date < pd.Timestamp(TRAIN_END) - embargo].dropna(subset=["next_range_pct"])
    cal = data[(data.date >= pd.Timestamp(CAL_START)) &
               (data.date < pd.Timestamp(CAL_END) - embargo)].dropna(subset=["next_range_pct"])
    holdout = data[data.date >= pd.Timestamp(HOLDOUT_START)].dropna(subset=["next_range_pct"])

    models, adjustments = {}, {}
    for name, quantile in QUANTILES.items():
        model = make_pipeline(SimpleImputer(), LGBMRegressor(objective="quantile", alpha=quantile,
            **CONFIG, verbosity=-1)).fit(train[FEATURES], train.next_range_pct)
        adjustments[name] = float(np.quantile(cal.next_range_pct - model.predict(cal[FEATURES]), quantile))
        models[name] = model

    predictions = np.column_stack([models[name].predict(holdout[FEATURES]) + adjustments[name]
                                   for name in QUANTILES])
    predictions = np.sort(np.maximum(predictions, 0), axis=1)
    actual = holdout.next_range_pct.to_numpy()
    reproduced = {}
    for position, (name, quantile) in enumerate(QUANTILES.items()):
        loss = np.maximum(quantile * (actual - predictions[:, position]),
                          (quantile - 1) * (actual - predictions[:, position]))
        reproduced[name] = {"pinball_loss": float(loss.mean()),
                            "coverage": float((actual <= predictions[:, position]).mean())}

    stored = json.loads((ROOT / "reports/phase3g_daily_range.json").read_text())["final_holdout"]
    mismatches = []
    for name, quantile in QUANTILES.items():
        expected_entry = stored["quantiles"][str(quantile)]
        for metric in ("pinball_loss", "coverage"):
            expected = expected_entry[metric]
            if abs(expected - reproduced[name][metric]) > 1e-6:
                mismatches.append((name, metric, expected, reproduced[name][metric]))
    if mismatches:
        raise SystemExit(f"artifact does not reproduce stored holdout: {mismatches}")

    metadata = {
        "model_id": MODEL_ID, "version": VERSION,
        "kind": "cash_session_range_quantiles", "instrument": "^NDX",
        "features": FEATURES, "quantiles": QUANTILES, "config": CONFIG,
        "calibration": "additive residual quantile from the 2022-2023 block",
        "train_rows": len(train), "calibration_rows": len(cal), "holdout_rows": len(holdout),
        "train_last": str(train.date.max().date()), "calibration_last": str(cal.date.max().date()),
        "holdout_first": str(holdout.date.min().date()), "holdout_last": str(holdout.date.max().date()),
        "adjustments": adjustments, "holdout_reproduced": reproduced,
        "dataset_sha256": hashlib.sha256(pd.util.hash_pandas_object(
            index[["date", "close", "high", "low", "volume"]], index=False).values.tobytes()).hexdigest(),
        "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
        "trading_decision": "NO_TRADE",
        "scope": "Nasdaq-100 cash-session high-low range as a fraction of the reference close; "
                 "not NQ futures and not a trading signal",
        "provenance": {"source": "yahoo_public_unofficial daily history",
                       "availability": "next UTC midnight after the session date"},
    }
    directory = save_artifact(ROOT / "models/shadow", MODEL_ID, models, metadata)
    (ROOT / "reports/phase3h_model_freeze.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"model": str(directory), "holdout": reproduced, "adjustments": adjustments}))


if __name__ == "__main__":
    main()
