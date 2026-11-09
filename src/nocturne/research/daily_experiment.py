"""Fixed development-only index-context experiment, never a futures strategy.

Historical Yahoo timestamps are availability lower bounds, not reconstructed
publication vintages. Previously inspected development eras are not independent
validation. No final (2024+) holdout is scored, even on repeated scheduled runs.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..adapters.yahoo_history import _frame, load_history
from ..adapters.snapshots import canonical, digest
from .validation import walk_forward

FEATURES = ["return_1", "return_5", "return_20", "volatility_20", "range_fraction"]
PROTOCOL = {"version": "index-development-v1", "symbols": ["^NDX", "^GSPC"],
            "development_start": "2000-01-01", "reserved_from": "2024-01-01",
            "min_train_days": 1500, "calibration_days": 250, "test_days": 250,
            "max_folds": 3, "embargo_days": 5, "C": .2, "seed": 7,
            "label": "next observed session close greater than its open",
            "holdout_policy": "2024+ excluded; previously studied history is development diagnostic only"}


def verified_history(root, symbol):
    name = symbol.replace("^", "IDX_").replace("=", "_")
    manifest = json.loads((root / "manifests" / f"{name}.json").read_text())
    raw = list((root / "raw").glob(f"*{manifest['raw_sha256']}*"))
    normalized = root / "normalized" / f"{name}.csv"
    if len(raw) != 1 or digest(raw[0].read_bytes()) != manifest["raw_sha256"] or digest(normalized.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("historical source checksum mismatch")
    payload = json.loads(raw[0].read_bytes())
    if payload["chart"]["result"][0]["meta"]["symbol"] != symbol:
        raise ValueError("historical source identity mismatch")
    frame = load_history(root, symbol)
    rebuilt = _frame(payload, symbol)
    pd.testing.assert_frame_equal(frame, rebuilt[list(frame.columns)], check_dtype=False, check_exact=False, rtol=0, atol=1e-10)
    if "source_complete" not in frame:
        # Legacy receipts predate this explicit flag; derive from the verified
        # archived quote arrays, never assume an imputed bar was complete.
        frame["source_complete"] = rebuilt.source_complete.to_numpy()
    values = frame[["open", "high", "low", "close", "volume"]].to_numpy(float)
    if (not np.isfinite(values).all() or (values[:, :4] <= 0).any() or (values[:, 4] < 0).any()
            or frame.date.duplicated().any() or not frame.timestamp.is_monotonic_increasing
            or not frame.available_at.is_monotonic_increasing
            or (frame.available_at <= frame.timestamp).any()):
        raise ValueError("invalid historical values or chronology")
    return frame, manifest


def build_dataset(frame, reserved_from=None):
    """reserved_from defaults to the protocol holdout; Phase 3U passes its own bound."""
    reserved_from = reserved_from or PROTOCOL["reserved_from"]
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    # Incomplete observations are not replaced or forward filled into features.
    complete = frame.source_complete.astype(str).str.lower().eq("true")
    close = frame.close.where(complete)
    returns = close.pct_change(fill_method=None)
    out = pd.DataFrame({"date": frame.date, "feature_available_at": frame.available_at,
                        "label_end": frame.available_at.shift(-1),
                        "entry_time": frame.timestamp.shift(-1),
                        "return_1": returns, "return_5": close / close.shift(5) - 1,
                        "return_20": close / close.shift(20) - 1,
                        "volatility_20": returns.rolling(20).std(),
                        "range_fraction": (frame.high - frame.low).where(complete) / close,
                        "next_return": (frame.close / frame.open - 1).shift(-1).where(complete.shift(-1, fill_value=False))})
    out["up"] = out.next_return.gt(0).astype(int)
    out["day"] = out.date
    out["signal_id"] = out.date
    out = out.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    out = out[(out.feature_available_at < out.entry_time)
              & (out.date >= PROTOCOL["development_start"])
              & (out.label_end < pd.Timestamp(reserved_from, tz="UTC"))]
    return out.reset_index(drop=True)


def folds(data):
    return walk_forward(data, min_train=PROTOCOL["min_train_days"], calibration_groups=PROTOCOL["calibration_days"],
                        test_groups=PROTOCOL["test_days"], embargo=pd.Timedelta(days=PROTOCOL["embargo_days"]))[:PROTOCOL["max_folds"]]


def train_development(data, destination):
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from ..ml.calibration import PlattCalibrator
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    splits = []
    for i, fold in enumerate(folds(data)):
        if fold.train.up.nunique() < 2 or fold.calibration.up.nunique() < 2:
            raise ValueError("insufficient development classes")
        model = make_pipeline(StandardScaler(), LogisticRegression(C=PROTOCOL["C"], max_iter=1000, random_state=7))
        model.fit(fold.train[FEATURES], fold.train.up)
        calibration = PlattCalibrator().fit(model.predict_proba(fold.calibration[FEATURES])[:, 1], fold.calibration.up.to_numpy())
        path = destination / f"fold_{i}.joblib"
        joblib.dump({"model": model, "calibrator": calibration, "frequency": float(fold.train.up.mean())}, path)
        splits.append({"fold": i, "model_sha256": digest(path.read_bytes()),
                       "train_rows": len(fold.train), "calibration_rows": len(fold.calibration), "test_rows": len(fold.test),
                       "train_end": str(fold.train.label_end.max()), "calibration_start": str(fold.calibration.feature_available_at.min()),
                       "calibration_end": str(fold.calibration.label_end.max()), "test_start": str(fold.test.feature_available_at.min()),
                       "test_end": str(fold.test.label_end.max())})
    if not splits:
        raise ValueError("insufficient walk-forward groups")
    return splits


def evaluate_development(data, destination, splits):
    import joblib
    from sklearn.metrics import roc_auc_score, balanced_accuracy_score, recall_score
    from ..ml.calibration import classification_metrics
    rows = []
    for i, fold in enumerate(folds(data)):
        path = Path(destination) / f"fold_{i}.joblib"
        if digest(path.read_bytes()) != splits[i]["model_sha256"]:
            raise ValueError("challenger artifact changed")
        artifact = joblib.load(path)
        test = fold.test[["date", "up"]].copy()
        test["p_model"] = artifact["calibrator"].predict(artifact["model"].predict_proba(fold.test[FEATURES])[:, 1])
        test["p_frequency"] = artifact["frequency"]
        test["fold"] = i
        rows.append(test)
    predictions = pd.concat(rows, ignore_index=True)
    metrics = {}
    for name in ("p_model", "p_frequency"):
        y, p = predictions.up.to_numpy(), predictions[name].to_numpy()
        metrics[name] = {**classification_metrics(y, p), "auc": float(roc_auc_score(y, p)),
                         "balanced_accuracy": float(balanced_accuracy_score(y, p >= .5)),
                         "class_recall": recall_score(y, p >= .5, labels=[0, 1], average=None).tolist()}
    return {"status": "DEVELOPMENT_DIAGNOSTIC_ONLY", "protocol": PROTOCOL, "folds": splits,
            "metrics": metrics, "holdout_scored": False, "decision": "NO_PROMOTION",
            "findings": "fixed logistic challenger; no search, no new incremental feature claim, no independent performance validation"}, predictions


def context_backtest(data):
    """Fixed prior-20-session sign rule, hypothetical index unit returns only."""
    direction = np.sign(data.return_20)
    gross = direction * data.next_return
    results = {}
    for bps in (0, 2, 5):
        net = gross - bps / 10000
        equity = (1 + net).cumprod()
        drawdown = equity / equity.cummax().clip(lower=1) - 1
        wins, losses = net[net > 0], net[net <= 0]
        results[str(bps)] = {"observations": len(net), "net_mean_fraction": float(net.mean()),
                             "average_win_fraction": float(wins.mean()) if len(wins) else None,
                             "average_loss_fraction": float(losses.mean()) if len(losses) else None,
                             "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else None,
                             "max_drawdown_fraction": float(-drawdown.min()),
                             "by_year": {str(year): {"n": len(group), "mean_fraction": float(group.net.mean())}
                                         for year, group in pd.DataFrame({"year": pd.to_datetime(data.date).dt.year, "net": net}).groupby("year")}}
    return {"strategy": "fixed prior-20-session momentum sign; next observed open-to-close",
            "scope": "NON_EXECUTABLE_INDEX_CONTEXT_NOT_NQ_ES_PNL", "costs": "hypothetical roundtrip basis points, not futures commissions",
            "sensitivity": results, "target_first": None, "stop_first": None, "mfe_mae": None,
            "limitations": ["no intraday barrier path", "index not executable", "current historical vintage", "development reuse"],
            "decision": "NO_PROMOTION", "trading_decision": "NO_TRADE"}
