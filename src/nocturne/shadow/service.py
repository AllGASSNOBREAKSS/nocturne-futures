"""Read-only shadow forecasting: eligibility, generation and maturation.

Fail-closed rules:
  * the data date must be the most recent completed trading day before the target
  * the daily bar must be available at the run timestamp
  * the target session must not have opened yet
  * VIX context must be fresh
No forecast is written when any rule fails; the reason is recorded instead.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import numpy as np
import pandas as pd

from ..market_clock import ET, is_trading_day
from .features import FeatureSnapshot, build_features
from .model import ShadowArtifact
from .store import ShadowStore, forecast_id

UTC = timezone.utc
RTH_OPEN = time(9, 30)
MAX_VIX_LAG_DAYS = 4


def previous_trading_day(day: date) -> date:
    candidate = day - timedelta(days=1)
    for _ in range(14):
        if is_trading_day(candidate):
            return candidate
        candidate -= timedelta(days=1)
    raise ValueError("no trading day found")


def next_trading_day(day: date) -> date:
    candidate = day + timedelta(days=1)
    for _ in range(14):
        if is_trading_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    raise ValueError("no trading day found")


def session_open(target: date) -> datetime:
    return datetime.combine(target, RTH_OPEN, ET).astimezone(UTC)


def _prepared(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out.date)
    if "available_at" in out:
        out["available_at"] = pd.to_datetime(out.available_at, utc=True)
    return out.sort_values("date").reset_index(drop=True)


def assess_eligibility(index_bars: pd.DataFrame, vix_bars: pd.DataFrame,
                       now: datetime) -> dict:
    """Return an eligibility decision without writing anything.

    The service forecasts the *current* session before its 13:30 UTC open. After
    the open it refuses, because the remaining session is not the validated
    horizon. On non-trading days it targets the next session.
    """
    now = now.astimezone(UTC)
    index = _prepared(index_bars)
    vix = _prepared(vix_bars)
    if index.empty:
        return {"eligible": False, "reason": "NO_INDEX_DATA"}
    available = index[index.available_at <= now] if "available_at" in index else index
    if available.empty:
        return {"eligible": False, "reason": "NO_AVAILABLE_INDEX_DATA"}
    data_date = available.date.iloc[-1].date()
    if not is_trading_day(data_date):
        return {"eligible": False, "reason": "DATA_DATE_NOT_TRADING_DAY", "data_date": str(data_date)}
    today = now.date()
    if is_trading_day(today) and now < session_open(today):
        target = today
    elif is_trading_day(today):
        return {"eligible": False, "reason": "TOO_LATE_FOR_TARGET", "data_date": str(data_date),
                "session_open_utc": session_open(today).isoformat()}
    else:
        target = next_trading_day(today)
        if now >= session_open(target):
            return {"eligible": False, "reason": "TOO_LATE_FOR_TARGET", "data_date": str(data_date)}
    required = previous_trading_day(target)
    if data_date < required:
        return {"eligible": False, "reason": "STALE_DATA_DATE", "data_date": str(data_date),
                "required_data_date": str(required), "target_date": str(target)}
    if data_date > required:
        return {"eligible": False, "reason": "DATA_AHEAD_OF_TARGET", "data_date": str(data_date),
                "target_date": str(target)}
    vix_available = vix[vix.available_at <= now] if "available_at" in vix else vix
    if vix_available.empty:
        return {"eligible": False, "reason": "NO_VIX_DATA"}
    vix_date = vix_available.date.iloc[-1].date()
    if (data_date - vix_date).days > MAX_VIX_LAG_DAYS:
        return {"eligible": False, "reason": "STALE_VIX", "vix_date": str(vix_date)}
    return {"eligible": True, "data_date": str(data_date), "target_date": str(target),
            "session_open_utc": session_open(target).isoformat()}


def generate(artifact: ShadowArtifact, store: ShadowStore, index_bars: pd.DataFrame,
             vix_bars: pd.DataFrame, now: datetime, validation_status: str,
             source: dict | None = None) -> dict:
    now = now.astimezone(UTC)
    decision = assess_eligibility(index_bars, vix_bars, now)
    if not decision["eligible"]:
        store.record_quality_failure(decision["reason"], decision)
        return {"status": "SKIPPED", **decision}
    snapshot = build_features(index_bars, vix_bars, now)
    quantiles = artifact.predict(snapshot)
    identifier = forecast_id(artifact.model_id, decision["target_date"], snapshot.digest())
    record = {
        "forecast_id": identifier,
        "model_id": artifact.model_id,
        "model_version": artifact.version,
        "instrument": "^NDX",
        "kind": "cash_session_range",
        "data_date": decision["data_date"],
        "target_date": decision["target_date"],
        "created_at": now.isoformat(),
        "session_open_utc": decision["session_open_utc"],
        "reference_close": snapshot.reference_close,
        "quantiles": quantiles,
        "interval_widths": {"p50": quantiles["p50"], "p80": quantiles["p80"] - quantiles["p50"],
                            "p90": quantiles["p90"] - quantiles["p50"]},
        "features": snapshot.values,
        "feature_digest": snapshot.digest(),
        "dataset_sha256": snapshot.dataset_sha256,
        "rows_used": snapshot.rows_used,
        "validation_status": validation_status,
        "trading_decision": "NO_TRADE",
        "source": source or {},
        "status": "PENDING",
        "notes": ["range is a percentage of the reference close",
                  "cash-session index range, not NQ futures",
                  "read-only research shadow; not a trading signal"],
    }
    stored = store.append_forecast(record)
    return {"status": "STORED", "forecast": stored, "eligibility": decision}


def evaluate_matured(store: ShadowStore, index_bars: pd.DataFrame, now: datetime) -> list[dict]:
    now = now.astimezone(UTC)
    index = _prepared(index_bars)
    if "available_at" not in index:
        return []
    by_date = {row.date.date().isoformat(): row for row in index.itertuples(index=False)}
    written = []
    existing = {item["forecast_id"] for item in store.outcomes()}
    for forecast in store.forecasts():
        if forecast["forecast_id"] in existing:
            continue
        bar = by_date.get(forecast["target_date"])
        if bar is None or pd.Timestamp(bar.available_at) > now:
            continue
        realized = (float(bar.high) - float(bar.low)) / float(forecast["reference_close"])
        covered = {name: bool(realized <= forecast["quantiles"][name]) for name in ("p50", "p80", "p90")}
        pinball = {}
        for name, quantile in (("p50", 0.5), ("p80", 0.8), ("p90", 0.9)):
            residual = realized - forecast["quantiles"][name]
            pinball[name] = float(max(quantile * residual, (quantile - 1) * residual))
        outcome = {
            "forecast_id": forecast["forecast_id"],
            "evaluated_at": now.isoformat(),
            "target_date": forecast["target_date"],
            "realized_high": float(bar.high),
            "realized_low": float(bar.low),
            "realized_range_pct": float(realized),
            "covered": covered,
            "pinball": pinball,
            "status": "MATURED",
        }
        written.append(store.append_outcome(outcome))
    return written


def evaluation_summary(store: ShadowStore) -> dict:
    forecasts = store.forecasts()
    outcomes = store.outcomes()
    if not outcomes:
        return {"matured": 0, "pending": len(forecasts), "status": "INSUFFICIENT_FORWARD_DATA",
                "note": "no forward forecast has matured; do not report accuracy",
                "quality_failures": len(store.quality_events())}
    by_id = {item["forecast_id"]: item for item in forecasts}
    frame = pd.DataFrame([{**outcome, "model_version": by_id.get(outcome["forecast_id"], {}).get("model_version"),
                           "vix_level": by_id.get(outcome["forecast_id"], {}).get("features", {}).get("vix_level"),
                           "month": outcome["target_date"][:7]} for outcome in outcomes])
    result = {"matured": len(frame), "pending": len(forecasts) - len(frame),
              "status": "SHADOW_EVALUATING" if len(frame) < 30 else "SHADOW_SAMPLE_DEVELOPING",
              "quality_failures": len(store.quality_events()),
              "coverage": {q: float(frame.covered.apply(lambda value: value[q]).mean()) for q in ("p50", "p80", "p90")},
              "mean_pinball": {q: float(frame.pinball.apply(lambda value: value[q]).mean()) for q in ("p50", "p80", "p90")},
              "median_width": {q: float(pd.Series([by_id[i]["interval_widths"][q]
                                                  for i in frame.forecast_id]).median())
                               for q in ("p50", "p80", "p90")},
              "by_month": {month: {"matured": len(group),
                                   "coverage_p80": float(group.covered.apply(lambda v: v["p80"]).mean())}
                           for month, group in frame.groupby("month")},
              "sample_warning": "forward samples are small; treat coverage as provisional",
              "trading_decision": "NO_TRADE"}
    return result
