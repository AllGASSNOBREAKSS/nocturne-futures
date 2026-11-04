"""Read-only shadow forecasting: eligibility, generation and maturation.

Fail-closed rules:
  * the data date must be the most recent completed trading day before the target
  * the daily bar must be available at the run timestamp
  * the target session must not have opened yet
  * VIX context must be fresh
No forecast is written when any rule fails; the reason is recorded instead.
"""
from __future__ import annotations

import hashlib
import json
from time import perf_counter
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
import pandas as pd

from ..market_clock import ET, is_trading_day
from .features import FEATURES, FeatureSnapshot, build_features
from .model import ShadowArtifact
from .store import ShadowStore, forecast_id
from .calendar import session_close, supported

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

    The service forecasts the *current* session before its 09:30 New York open. After
    the open it refuses, because the remaining session is not the validated
    horizon. On non-trading days it targets the next session.
    """
    now = now.astimezone(UTC)
    if not supported(now.date()):
        return {"eligible": False, "reason": "CALENDAR_OUT_OF_RANGE"}
    if any("available_at" not in frame for frame in (index_bars, vix_bars)):
        return {"eligible": False, "reason": "AVAILABILITY_MISSING"}
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
              source: dict | None = None, issuance_clock=None) -> dict:
    now = now.astimezone(UTC)
    if artifact.model_id != "ndx-range-v1" or validation_status != "RESEARCH_VALIDATED_PENDING_SHADOW":
        store.record_quality_failure("MODEL_NOT_ELIGIBLE")
        return {"status": "SKIPPED", "reason": "MODEL_NOT_ELIGIBLE"}
    decision = assess_eligibility(index_bars, vix_bars, now)
    if not decision["eligible"]:
        if decision["reason"] != "TOO_LATE_FOR_TARGET":
            store.record_quality_failure(decision["reason"], decision)
        return {"status": "SKIPPED", **decision}
    for previous in store.forecasts():
        if (previous["model_id"] == artifact.model_id and previous.get("instrument") == "^NDX"
                and previous.get("kind") == "cash_session_range"
                and previous["target_date"] == decision["target_date"]):
            return {"status": "ALREADY_ISSUED", "forecast": previous, "eligibility": decision}
    started = perf_counter()
    snapshot = build_features(index_bars, vix_bars, now)
    quantiles = artifact.predict(snapshot)
    issued_at = issuance_clock() if issuance_clock is not None else now
    if issued_at.tzinfo is None or issued_at < now:
        store.record_quality_failure("ISSUANCE_CLOCK_INVALID")
        return {"status": "SKIPPED", "reason": "ISSUANCE_CLOCK_INVALID"}
    if issued_at >= pd.Timestamp(decision["session_open_utc"]):
        store.record_quality_failure("DEADLINE_PASSED_DURING_INFERENCE")
        return {"status": "SKIPPED", "reason": "DEADLINE_PASSED_DURING_INFERENCE"}
    identifier = forecast_id(artifact.model_id, decision["target_date"], snapshot.digest())
    record = {
        "forecast_id": identifier,
        "model_id": artifact.model_id,
        "model_version": artifact.version,
        "inference_revision": "residual-adjusted-v1",
        "calibration_status": "FROZEN_RESIDUAL_ADJUSTMENTS_APPLIED",
        "data_quality_status": "PASSED",
        "instrument": "^NDX",
        "kind": "cash_session_range",
        "data_date": decision["data_date"],
        "target_date": decision["target_date"],
        "created_at": issued_at.astimezone(UTC).isoformat(),
        "feature_asof": now.isoformat(),
        "prediction_compute_seconds": perf_counter() - started,
        "issuance_lead_seconds": (pd.Timestamp(decision["session_open_utc"]) - issued_at).total_seconds(),
        "session_open_utc": decision["session_open_utc"],
        "reference_close": snapshot.reference_close,
        "quantiles": quantiles,
        "baseline_quantiles": artifact.metadata.get("baseline_quantiles"),
        "interval_widths": {"p50": quantiles["p50"], "p80": quantiles["p80"] - quantiles["p50"],
                            "p90": quantiles["p90"] - quantiles["p50"]},
        "features": snapshot.values,
        "feature_digest": snapshot.digest(),
        "dataset_sha256": snapshot.dataset_sha256,
        "dataset_digest_format": "feature-input-csv-lf-v1",
        "rows_used": snapshot.rows_used,
        "validation_status": validation_status,
        "trading_decision": "NO_TRADE",
        "source": source or {},
        "market_snapshot_ids": (source or {}).get("snapshot_ids"),
        "artifact_digests": artifact.metadata.get("artifact_digests"),
        "status": "PENDING",
        "notes": ["range is a percentage of the reference close",
                  "cash-session index range, not NQ futures",
                  "read-only research shadow; not a trading signal"],
    }
    from ..adapters.snapshots import canonical, digest
    record["record_sha256"] = digest(canonical(record))
    stored = store.append_forecast(record)
    return {"status": "STORED", "forecast": stored, "eligibility": decision}


def evaluate_matured(store: ShadowStore, index_bars: pd.DataFrame, now: datetime,
                     allowed_forecast_ids: set[str] | None = None,
                     verified_reconciliation_ids: dict | None = None) -> list[dict]:
    now = now.astimezone(UTC)
    index = _prepared(index_bars)
    if "available_at" not in index:
        return []
    by_date = {row.date.date().isoformat(): row for row in index.itertuples(index=False)}
    written = []
    existing = {item["forecast_id"] for item in store.outcomes()}
    for forecast in store.forecasts():
        if allowed_forecast_ids is not None and forecast["forecast_id"] not in allowed_forecast_ids:
            continue
        if forecast["forecast_id"] in existing:
            continue
        bar = by_date.get(forecast["target_date"])
        if bar is None or pd.Timestamp(bar.available_at) > now:
            continue
        target = date.fromisoformat(forecast["target_date"])
        try:
            close = session_close(target)
            prices = np.array([bar.open, bar.high, bar.low, bar.close], dtype=float)
            valid = (np.isfinite(prices).all() and (prices > 0).all()
                     and bar.high >= max(bar.open, bar.close, bar.low)
                     and bar.low <= min(bar.open, bar.close, bar.high)
                     and float(forecast["reference_close"]) > 0
                     and pd.Timestamp(forecast["created_at"]) < session_open(target)
                     and pd.Timestamp(bar.available_at) >= close
                     and now >= close
                     and getattr(bar, "source_complete", True) in (True, "True")
                     and not index.date.duplicated().any())
        except (ValueError, TypeError):
            valid = False
        if not valid:
            store.record_quality_failure("OUTCOME_DATA_BLOCKED", {"forecast_id": forecast["forecast_id"]})
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
            "realized_range_points": float(bar.high - bar.low),
            "reference_close": forecast["reference_close"],
            "forecast_points": {k: v * forecast["reference_close"] for k, v in forecast["quantiles"].items()},
            "source_available_at": pd.Timestamp(bar.available_at).isoformat(),
            "availability_basis": "conservative adapter bound, not exact exchange publication time",
            "outcome_bar_sha256": hashlib.sha256(str(bar).encode()).hexdigest(),
            "data_quality_status": "PASSED",
            "inference_revision": forecast.get("inference_revision", "legacy-unadjusted"),
            "forecast_sha256": hashlib.sha256(json.dumps(forecast, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
            "market_snapshot_id": index_bars.attrs.get("snapshot_id"),
            "source_reliability": "research_grade_unofficial_not_exchange_finality",
            "reconciliation_ids": (verified_reconciliation_ids or {}).get(forecast["forecast_id"], []),
            "covered": covered,
            "pinball": pinball,
            "status": "MATURED",
        }
        written.append(store.append_outcome(outcome))
    return written


def evaluation_summary(store: ShadowStore) -> dict:
    forecasts = store.forecasts()
    outcomes = store.outcomes()
    missed = store.missed()
    if not outcomes:
        return {"matured": 0, "pending": len(forecasts), "status": "INSUFFICIENT_FORWARD_DATA",
                "note": "no forward forecast has matured; do not report accuracy",
                "quality_failures": len(store.quality_events()),
                "missed": len(missed),
                "milestones": {str(n): {"target": n, "matured": 0, "remaining": n,
                                        "reached": False} for n in (30, 60, 90)}}
    by_id = {item["forecast_id"]: item for item in forecasts}
    rows = []
    for outcome in sorted(outcomes, key=lambda item: item["target_date"]):
        forecast = by_id.get(outcome["forecast_id"], {})
        rows.append({**outcome,
                     "model_version": forecast.get("model_version"),
                     "vix_level": forecast.get("features", {}).get("vix_level"),
                     "month": outcome["target_date"][:7],
                     "baseline_quantiles": forecast.get("baseline_quantiles")})
    frame = pd.DataFrame(rows)
    from ..research.level_reactions import wilson

    def coverage_interval(column: str) -> dict:
        successes = int(frame.covered.apply(lambda value: value[column]).sum())
        low, high = wilson(successes, len(frame))
        return {"rate": successes / len(frame), "low": low, "high": high, "n": len(frame)}

    baseline_loss = {}
    for name, quantile in (("p50", 0.5), ("p80", 0.8), ("p90", 0.9)):
        values = []
        for _, row in frame.iterrows():
            baseline = (row.baseline_quantiles or {}).get(name)
            if baseline is None:
                continue
            residual = row.realized_range_pct - baseline
            values.append(max(quantile * residual, (quantile - 1) * residual))
        baseline_loss[name] = float(np.mean(values)) if values else None

    def regime(value):
        if value is None or not np.isfinite(value):
            return "UNKNOWN"
        if value < 0.8:
            return "LOW_VOL"
        if value > 1.2:
            return "HIGH_VOL"
        return "NORMAL_VOL"

    frame["regime"] = frame.vix_level.apply(regime)
    drift = None
    if len(frame) >= 10:
        half = len(frame) // 2
        first = frame.iloc[:half].covered.apply(lambda value: value["p80"]).mean()
        second = frame.iloc[half:].covered.apply(lambda value: value["p80"]).mean()
        drift = {"p80_first_half": float(first), "p80_second_half": float(second),
                 "delta": float(second - first)}
    result = {"matured": len(frame), "pending": len(forecasts) - len(frame),
              "status": "SHADOW_EVALUATING" if len(frame) < 30 else "SHADOW_SAMPLE_DEVELOPING",
              "quality_failures": len(store.quality_events()),
              "missed": len(missed),
              "coverage": {q: float(frame.covered.apply(lambda value: value[q]).mean()) for q in ("p50", "p80", "p90")},
              "coverage_interval": {q: coverage_interval(q) for q in ("p50", "p80", "p90")},
              "mean_pinball": {q: float(frame.pinball.apply(lambda value: value[q]).mean()) for q in ("p50", "p80", "p90")},
              "baseline_pinball": baseline_loss,
              "by_inference_revision": {
                  revision: {"matured": len(items), "coverage_p80": float(np.mean([item["covered"]["p80"] for item in items]))}
                  for revision in sorted({by_id[o["forecast_id"]].get("inference_revision", "legacy-unadjusted") for o in outcomes})
                  for items in [[o for o in outcomes if by_id[o["forecast_id"]].get("inference_revision", "legacy-unadjusted") == revision]]},
              "median_width": {q: float(pd.Series([by_id[i]["interval_widths"][q]
                                                  for i in frame.forecast_id]).median())
                               for q in ("p50", "p80", "p90")},
              "by_month": {month: {"matured": len(group),
                                   "coverage_p80": float(group.covered.apply(lambda v: v["p80"]).mean())}
                           for month, group in frame.groupby("month")},
              "by_volatility_regime": {name: {"matured": len(group),
                                              "coverage_p80": float(group.covered.apply(lambda v: v["p80"]).mean())}
                                       for name, group in frame.groupby("regime")},
              "drift": drift,
              "milestones": {str(n): {"target": n, "matured": len(frame),
                                      "remaining": max(0, n - len(frame)),
                                      "reached": len(frame) >= n} for n in (30, 60, 90)},
              "sample_warning": "forward samples are small; treat coverage as provisional",
              "trading_decision": "NO_TRADE"}
    return result


def record_missed(store: ShadowStore, index_bars: pd.DataFrame | None, now: datetime,
                  lookback_days: int = 30) -> list[dict]:
    """Record passed deadlines after activation, independent of market data.

    Legacy index_bars/lookback_days parameters are retained for compatibility;
    recovery scans the entire service lifetime, never just a 30-day window.
    """
    now = now.astimezone(UTC)
    meta = store.meta()
    if not meta:
        return []
    start = pd.Timestamp(meta["service_start"]).date()
    forecast_dates = {item["target_date"] for item in store.forecasts()}
    existing = {item["target_date"] for item in store.missed()}
    written = []
    first = start
    for stamp in pd.date_range(first, now.date()):
        day = stamp.date()
        if not supported(day) or not is_trading_day(day) or now < session_open(day):
            continue
        if pd.Timestamp(meta["service_start"]) >= session_open(day):
            continue
        key = day.isoformat()
        if key in forecast_dates or key in existing:
            continue
        written.append(store.append_missed({
            "target_date": key,
            "recorded_at": now.isoformat(),
            "reason": "NO_FORECAST_ISSUED",
            "service_start": meta["service_start"],
            "model_id": meta.get("model_id"),
        }))
    return written


def audit_forecasts(store: ShadowStore, index_bars: pd.DataFrame, snapshot_root=None) -> dict:
    """Verify immutability invariants without rewriting anything."""
    index = _prepared(index_bars)
    closes = {row.date.date().isoformat(): float(row.close) for row in index.itertuples(index=False)}
    checks = []
    for forecast in store.forecasts():
        issues = []
        warnings = []
        reconciliation_id = None
        if forecast.get("record_sha256"):
            from ..adapters.snapshots import canonical, digest
            if forecast["record_sha256"] != digest(canonical({k: v for k, v in forecast.items() if k != "record_sha256"})):
                issues.append("FORECAST_RECORD_HASH_MISMATCH")
        if forecast.get("market_snapshot_ids"):
            try:
                from ..adapters.snapshots import SnapshotStore
                from .reconciliation import verify_issuance
                verify_issuance(forecast, SnapshotStore(snapshot_root), forecast["market_snapshot_ids"])
            except (ValueError, KeyError, OSError, TypeError):
                issues.append("ISSUANCE_SNAPSHOT_INVALID")
        quantiles = forecast["quantiles"]
        if not (quantiles["p50"] <= quantiles["p80"] <= quantiles["p90"]):
            issues.append("NON_MONOTONE_QUANTILES")
        ordered = {name: forecast["features"].get(name) for name in FEATURES}
        if any(value is None for value in ordered.values()):
            issues.append("FEATURE_SCHEMA_INCOMPLETE")
        else:
            digest = hashlib.sha256(
                f"{forecast['data_date']}|{forecast['reference_close']}|{ordered}|"
                f"{forecast['dataset_sha256']}".encode()).hexdigest()
            if digest != forecast["feature_digest"]:
                issues.append("FEATURE_DIGEST_MISMATCH")
        expected_close = closes.get(forecast["data_date"])
        if expected_close is None:
            issues.append("DATA_DATE_BAR_MISSING")
        elif abs(expected_close - forecast["reference_close"]) > 1e-6:
            reconciled = False
            if snapshot_root is not None:
                from ..adapters.snapshots import SnapshotStore
                from .reconciliation import verify_reconciliation
                for record in store.reconciliations():
                    try:
                        reconciled = verify_reconciliation(forecast, record, SnapshotStore(snapshot_root), expected_close)
                    except (ValueError, KeyError, OSError, TypeError, IndexError):
                        continue
                    if reconciled:
                        reconciliation_id = record["reconciliation_id"]
                        break
            if reconciled:
                warnings.append("SOURCE_REVISION_RECONCILED_AS_ISSUED")
            else:
                issues.append("REFERENCE_CLOSE_MISMATCH")
        if pd.Timestamp(forecast["created_at"]) >= pd.Timestamp(forecast["session_open_utc"]):
            issues.append("ISSUED_AFTER_SESSION_OPEN")
        checks.append({"forecast_id": forecast["forecast_id"], "ok": not issues, "issues": issues,
                       "stored_reference_close": forecast["reference_close"],
                       "current_source_reference_close": expected_close})
        checks[-1]["warnings"] = warnings
        checks[-1]["reconciliation_id"] = reconciliation_id
    return {"forecasts": len(checks), "passed": sum(item["ok"] for item in checks),
            "failed": [item for item in checks if not item["ok"]], "records": checks}


def health(store: ShadowStore, now: datetime) -> dict:
    now = now.astimezone(UTC)
    forecasts = store.forecasts()
    outcomes = store.outcomes()
    events = store.log_events()
    successes = [event for event in events if event["event"] == "CYCLE_OK" and pd.Timestamp(event["at"]) <= now]
    last_run = successes[-1]["at"] if successes else None
    age_hours = None
    if last_run:
        age_hours = (now - pd.Timestamp(last_run).to_pydatetime()).total_seconds() / 3600
    pending = len(forecasts) - len(outcomes)
    recent_failures = [event for event in store.quality_events()
                       if 0 <= (now - pd.Timestamp(event["at"]).to_pydatetime()).total_seconds() <= 86400]
    warnings = []
    if last_run is None:
        warnings.append("NO_RUN_RECORDED")
    elif age_hours is not None and age_hours > 48:
        warnings.append("STALE_SERVICE")
    if recent_failures:
        warnings.append("RECENT_DATA_QUALITY_FAILURES")
    if pending > 5:
        warnings.append("LARGE_PENDING_BACKLOG")
    return {"status": "ok" if not warnings else "degraded", "warnings": warnings,
            "last_run": last_run, "age_hours": age_hours,
            "forecasts": len(forecasts), "matured": len(outcomes), "pending": pending,
            "missed": len(store.missed()),
            "recent_quality_failures": len(recent_failures),
            "trading_decision": "NO_TRADE"}
