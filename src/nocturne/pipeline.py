"""Training and research-forecast pipeline.

This module never places orders. It trains baselines on committed daily bars,
evaluates them walk-forward, and can emit a RESEARCH_ONLY forecast.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import (
    Bias,
    Decision,
    Prediction,
    Quality,
    ResearchStatus,
    Zone,
)
from .instruments import get_instrument
from .journal import PredictionJournal
from .ml.baseline import FrequencyBaseline, GradientBoostedBaseline, LogisticBaseline
from .ml.calibration import PlattCalibrator
from .ml.registry import ModelRecord, dataset_hash, save_model
from .research.dataset import binary_sample, build_training_frame
from .research.features import FEATURE_COLUMNS, build_daily_features
from .research.walk_forward import walk_forward

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "studies" / "daily_15y"
MARKET_CSV = ROOT / "data" / "market" / "daily"
REGISTRY = ROOT / "models" / "registry"
JOURNAL = ROOT / "data" / "journal"


def load_daily_csv(instrument_id: str, root: Path | None = None) -> pd.DataFrame:
    base = root or MARKET_CSV
    path = base / f"{instrument_id.upper()}.csv"
    if not path.exists():
        path = DATA_CSV / f"{instrument_id.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return frame[["date", "open", "high", "low", "close"]].sort_values("date").reset_index(drop=True)


def train_instrument(
    instrument_id: str,
    registry_root: Path | None = None,
    min_train: int = 750,
    step: int = 21,
) -> dict:
    registry_root = registry_root or REGISTRY
    bars = load_daily_csv(instrument_id)
    frame = build_training_frame(bars, target_atr=1.5, stop_atr=1.0, horizon=5)
    binary = binary_sample(frame)
    if len(binary) < min_train + step:
        raise ValueError(f"not enough binary samples for {instrument_id}: {len(binary)}")

    candidates = {
        "frequency": FrequencyBaseline,
        "logistic": LogisticBaseline,
        "hist_gradient_boosting": lambda: GradientBoostedBaseline(max_iter=100),
    }
    results = {}
    for name, factory in candidates.items():
        try:
            results[name] = walk_forward(
                frame,
                model_factory=factory,
                model_name=name,
                min_train=min_train,
                step=step,
            )
        except Exception as exc:  # noqa: BLE001 - research report captures failures
            results[name] = exc

    valid = {name: r for name, r in results.items() if not isinstance(r, Exception)}
    if not valid:
        raise RuntimeError("all baseline models failed")

    best_name = min(valid, key=lambda name: valid[name].metrics["brier"])
    best = valid[best_name]
    frequency_brier = valid.get("frequency", best).metrics["brier"]
    promoted = best.metrics["brier"] < frequency_brier - 0.005 and best.metrics["n"] >= 300

    sample = binary.dropna(subset=FEATURE_COLUMNS + ["y"]).reset_index(drop=True)
    split = int(len(sample) * 0.8)
    fit, calibration = sample.iloc[:split], sample.iloc[split:]
    model = candidates[best_name]()
    model.fit(fit[FEATURE_COLUMNS], fit["y"])
    calibrator = PlattCalibrator().fit(
        model.predict_proba(calibration[FEATURE_COLUMNS])[:, 1],
        calibration["y"].to_numpy(),
    )
    bundle = {"model": model, "calibrator": calibrator, "feature_columns": FEATURE_COLUMNS}

    model_id = f"{instrument_id.upper()}-{best_name}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}"
    record = ModelRecord(
        model_id=model_id,
        instrument_id=instrument_id.upper(),
        model_type=best_name,
        version="0.2.0",
        created_at=datetime.now(UTC).isoformat(),
        feature_columns=FEATURE_COLUMNS,
        train_start=str(sample["date"].iloc[0]),
        train_end=str(sample["date"].iloc[split - 1]),
        test_start=str(best.predictions["date"].iloc[0]),
        test_end=str(best.predictions["date"].iloc[-1]),
        metrics=best.metrics,
        dataset_sha256=dataset_hash(sample),
        calibration="platt",
        coefficients=model.coefficients(FEATURE_COLUMNS) if hasattr(model, "coefficients") else {},
        notes=[
            f"promotion_status={'CANDIDATE' if promoted else 'RESEARCH_ONLY'}",
            f"baseline_frequency_brier={frequency_brier}",
            "walk_forward_chronological=true",
            "same_bar_ambiguity=EXCLUDED",
        ],
    )
    save_model(registry_root, record, model=bundle)

    summary = {
        "instrument": instrument_id.upper(),
        "model_id": model_id,
        "best_model": best_name,
        "promotion_status": "CANDIDATE" if promoted else "RESEARCH_ONLY",
        "samples": int(len(binary)),
        "models": {
            name: (
                result.metrics
                if not isinstance(result, Exception)
                else {"error": str(result)}
            )
            for name, result in results.items()
        },
    }
    (registry_root / model_id / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _latest_bundle(registry_root: Path, instrument_id: str) -> tuple[Path, dict]:
    candidates = []
    for path in registry_root.glob(f"{instrument_id.upper()}-*/metadata.json"):
        meta = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((meta["created_at"], path.parent))
    if not candidates:
        raise FileNotFoundError(f"no trained model for {instrument_id}")
    _, directory = max(candidates, key=lambda item: item[0])
    import joblib

    return directory, joblib.load(directory / "model.joblib")


def make_forecast(
    instrument_id: str,
    registry_root: Path | None = None,
    journal_root: Path | None = None,
) -> Prediction:
    registry_root = registry_root or REGISTRY
    journal_root = journal_root or JOURNAL
    spec = get_instrument(instrument_id)
    directory, bundle = _latest_bundle(registry_root, instrument_id)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))

    bars = load_daily_csv(instrument_id)
    features = build_daily_features(bars).dropna(subset=FEATURE_COLUMNS).reset_index(drop=True)
    latest = features.iloc[-1]
    x = latest[FEATURE_COLUMNS].to_frame().T
    raw = bundle["model"].predict_proba(x)[:, 1]
    probability = float(bundle["calibrator"].predict(raw)[0])

    atr = float(latest["atr14"])
    last_close = float(bars["close"].iloc[-1])
    entry = last_close
    stop = entry - 1.0 * atr
    targets = [entry + 1.5 * atr, entry + 2.5 * atr]
    bias = Bias.BULLISH if probability >= 0.55 else Bias.BEARISH if probability <= 0.45 else Bias.NEUTRAL

    asof = datetime.strptime(str(bars["date"].iloc[-1]), "%Y-%m-%d").replace(
        hour=21, tzinfo=UTC
    )
    feature_hash = hashlib.sha256(
        json.dumps({k: float(latest[k]) for k in FEATURE_COLUMNS}, sort_keys=True).encode()
    ).hexdigest()[:16]

    def zone(price: float) -> Zone:
        half = 0.25 * atr
        return Zone(
            lower_price_ticks=spec.price_to_ticks(price - half),
            upper_price_ticks=spec.price_to_ticks(price + half),
        )

    from .contracts import Target
    from .risk import RiskContext, evaluate_risk

    risk = evaluate_risk(
        RiskContext(
            now=datetime.now(UTC),
            watermark=asof,
            coverage=1.0,
            critical_day_state="NORMAL",
            minutes_to_event=None,
            atr_percentile=None,
            market_open=True,
            signal_expires_at=asof + timedelta(days=5),
            duplicate=False,
            expected_value_points=None,
        )
    )
    decision = Decision.WAIT if risk.allow_new_risk else Decision.NO_TRADE

    prediction = Prediction(
        prediction_id=f"{instrument_id.upper()}-{asof.strftime('%Y%m%d')}-{datetime.now(UTC).strftime('%H%M%S')}",
        instrument_id=spec.instrument_id,
        contract_id=None,
        asof_utc=asof,
        data_watermark_utc=asof,
        expires_at_utc=asof + timedelta(days=5),
        horizon_seconds=5 * 86400,
        bias=bias,
        decision=decision,
        market_regime="TREND_UP" if float(latest["sma50_dist"]) > 0 else "TREND_DOWN",
        critical_day_state="NORMAL",
        strategy_id="research_daily_barrier",
        strategy_version="0.1.0",
        model_version=metadata["model_id"],
        feature_snapshot_hash=feature_hash,
        p_entry_fill=1.0,
        entry=zone(entry),
        stop=zone(stop),
        targets=[
            Target(
                target_id=f"TP{i + 1}",
                zone=zone(price),
                event_definition="close >= target before close <= stop within 5 sessions",
                p_target_before_stop_given_fill=None,
            )
            for i, price in enumerate(targets)
        ],
        expected_net_value_points=None,
        data_quality=Quality(coverage=1.0),
        reason_codes=[
            "RESEARCH_ONLY",
            "MODEL_NOT_PROMOTED",
            f"CALIBRATED_P_TP_FIRST={probability:.4f}",
            *risk.reason_codes,
        ],
        research_status=ResearchStatus.RESEARCH_ONLY,
        latency_ms=None,
    )
    PredictionJournal(journal_root).append(prediction)
    return prediction
