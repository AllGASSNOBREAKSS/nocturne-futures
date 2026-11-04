import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from nocturne.shadow import (FEATURES, ShadowStore, audit_forecasts,
                             evaluation_summary, health, record_missed)
from nocturne.shadow.service import assess_eligibility

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]


def bars(start="2025-03-17", periods=8):
    dates = pd.bdate_range(start, periods=periods)
    close = 100.0 + pd.Series(range(periods), index=dates)
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "timestamp": dates.tz_localize("UTC"),
        "available_at": (dates + pd.Timedelta(days=1)).tz_localize("UTC"),
        "open": close.to_numpy(), "high": (close + 1).to_numpy(),
        "low": (close - 1).to_numpy(), "close": close.to_numpy(), "volume": 1000.0,
    })


def forecast(identifier="f1", data_date="2025-03-24", target="2025-03-25",
             features=None, digest="d"):
    return {"forecast_id": identifier, "model_id": "ndx-range-v1",
            "model_version": "1.0.0", "instrument": "^NDX", "kind": "cash_session_range",
            "data_date": data_date, "target_date": target,
            "created_at": "2025-03-25T01:00:00+00:00",
            "session_open_utc": "2025-03-25T13:30:00+00:00",
            "reference_close": 100.0,
            "quantiles": {"p50": 0.01, "p80": 0.02, "p90": 0.03},
            "interval_widths": {"p50": 0.01, "p80": 0.01, "p90": 0.01},
            "features": features or {"atr_pct": 0.01}, "feature_digest": digest,
            "dataset_sha256": "x", "rows_used": 300,
            "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
            "trading_decision": "NO_TRADE", "source": {}, "status": "PENDING", "notes": []}


def test_missed_sessions_are_recorded_once_and_only_after_start(tmp_path):
    store = ShadowStore(tmp_path)
    store.ensure_started(datetime(2025, 3, 20, 1, tzinfo=UTC), "ndx-range-v1")
    index = bars()
    now = datetime(2025, 3, 26, 2, tzinfo=UTC)
    missed = record_missed(store, index, now)
    dates = [item["target_date"] for item in missed]
    assert dates == ["2025-03-20", "2025-03-21", "2025-03-24", "2025-03-25"]
    assert record_missed(store, index, now) == []
    assert len(store.missed()) == 4


def test_existing_forecast_is_not_marked_missed(tmp_path):
    store = ShadowStore(tmp_path)
    store.ensure_started(datetime(2025, 3, 20, 1, tzinfo=UTC), "ndx-range-v1")
    store.append_forecast(forecast())
    missed = record_missed(store, bars(), datetime(2025, 3, 26, 2, tzinfo=UTC))
    assert "2025-03-25" not in {item["target_date"] for item in missed}


def test_audit_detects_tampered_feature_digest(tmp_path):
    store = ShadowStore(tmp_path)
    features = {name: 0.01 for name in FEATURES}
    record = forecast(features=features, digest="not-the-right-digest")
    store.append_forecast(record)
    result = audit_forecasts(store, bars())
    assert result["passed"] == 0
    assert "FEATURE_DIGEST_MISMATCH" in result["failed"][0]["issues"]


def test_audit_reports_incomplete_feature_schema_without_raising(tmp_path):
    store = ShadowStore(tmp_path)
    store.append_forecast(forecast(features={"atr_pct": 0.01}))
    result = audit_forecasts(store, bars())
    assert result["passed"] == 0
    assert "FEATURE_SCHEMA_INCOMPLETE" in result["failed"][0]["issues"]


def test_health_flags_missing_run_and_recovers(tmp_path):
    store = ShadowStore(tmp_path)
    state = health(store, datetime(2025, 3, 26, 2, tzinfo=UTC))
    assert state["status"] == "degraded" and "NO_RUN_RECORDED" in state["warnings"]
    store.log("CYCLE_OK", now=datetime(2025, 3, 26, 2, tzinfo=UTC))
    recovered = health(store, datetime(2025, 3, 26, 2, tzinfo=UTC))
    assert recovered["status"] == "ok"


def test_evaluation_milestones_and_intervals(tmp_path):
    store = ShadowStore(tmp_path)
    empty = evaluation_summary(store)
    assert empty["milestones"]["30"]["remaining"] == 30
    for index in range(4):
        store.append_forecast(forecast(identifier=f"f{index}", target=f"2025-04-0{index + 1}"))
        store.append_outcome({"forecast_id": f"f{index}", "evaluated_at": "2025-04-02T00:00:00+00:00",
                              "target_date": f"2025-04-0{index + 1}", "realized_high": 102.0,
                              "realized_low": 99.0, "realized_range_pct": 0.02 if index % 2 else 0.005,
                              "covered": {"p50": index % 2 == 0, "p80": True, "p90": True},
                              "pinball": {"p50": 0.001, "p80": 0.002, "p90": 0.003},
                              "status": "MATURED"})
    summary = evaluation_summary(store)
    assert summary["matured"] == 4
    assert summary["coverage"]["p80"] == 1.0
    assert summary["coverage_interval"]["p80"]["low"] is not None
    assert summary["milestones"]["30"]["remaining"] == 26
    assert summary["by_volatility_regime"]["UNKNOWN"]["matured"] == 4
    assert summary["drift"] is None


def test_eligibility_uses_current_session_before_open():
    index = bars()
    vix = bars()
    now = datetime(2025, 3, 25, 1, tzinfo=UTC)
    result = assess_eligibility(index, vix, now)
    assert result["eligible"] is True
    assert result["target_date"] == "2025-03-25"
    after_open = assess_eligibility(index, vix, datetime(2025, 3, 25, 14, tzinfo=UTC))
    assert after_open["reason"] == "TOO_LATE_FOR_TARGET"


def test_store_prevents_revised_snapshot_second_issuance(tmp_path):
    store = ShadowStore(tmp_path)
    store.append_forecast(forecast())
    with pytest.raises(ValueError, match="already issued"):
        store.append_forecast(forecast(identifier="new-digest-new-id", digest="revised"))
    assert len(store.forecasts()) == 1


def test_concurrent_store_writers_are_serialized(tmp_path):
    def append(_):
        return ShadowStore(tmp_path).append_forecast(forecast())
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(append, range(12)))
    assert len(ShadowStore(tmp_path).forecasts()) == 1


def test_os_lock_recovers_after_process_death(tmp_path):
    from nocturne.shadow.locking import FileLock
    path = tmp_path / "cycle.lock"
    code = ("import os; from nocturne.shadow.locking import FileLock; "
            f"lock=FileLock({str(path)!r}); lock.acquire(); os._exit(7)")
    result = subprocess.run([sys.executable, "-c", code], timeout=30)
    assert result.returncode == 7
    lock = FileLock(path)
    assert lock.acquire(blocking=False)
    contender = FileLock(path)
    assert not contender.acquire(blocking=False)
    lock.release()
    assert contender.acquire(blocking=False)
    contender.release()


def test_partial_journal_fails_closed(tmp_path):
    store = ShadowStore(tmp_path)
    store.forecast_path.write_text('{"forecast_id":')
    with pytest.raises(ValueError):
        store.append_forecast(forecast())
    assert store.forecast_path.read_text() == '{"forecast_id":'


def test_failure_logs_cannot_mask_stale_health(tmp_path):
    store = ShadowStore(tmp_path)
    now = datetime(2026, 11, 4, 2, tzinfo=UTC)
    store.log("CYCLE_OK", now=datetime(2026, 10, 30, 2, tzinfo=UTC))
    store.log("CYCLE_FAILED", now=now)
    assert "STALE_SERVICE" in health(store, now)["warnings"]


def test_cash_calendar_dst_and_early_close():
    from datetime import date
    from nocturne.shadow.calendar import session_close
    from nocturne.shadow.service import session_open
    assert session_open(date(2026, 10, 30)).hour == 13
    assert session_open(date(2026, 11, 2)).hour == 14
    assert session_close(date(2026, 11, 27)).hour == 18
    assert session_close(date(2027, 12, 23)).hour == 21
    with pytest.raises(ValueError):
        session_close(date(2028, 1, 3))


def test_misses_are_recorded_without_provider_bars_after_long_outage(tmp_path):
    store = ShadowStore(tmp_path)
    store.ensure_started(datetime(2026, 9, 1, 1, tzinfo=UTC), "ndx-range-v1")
    written = record_missed(store, None, datetime(2026, 11, 4, 15, tzinfo=UTC))
    assert len(written) > 30
    assert written[-1]["target_date"] == "2026-11-04"
    assert record_missed(store, None, datetime(2026, 11, 4, 15, tzinfo=UTC)) == []


def test_operational_snapshot_requires_fresh_verified_receipt(tmp_path, monkeypatch):
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("shadow_runner_test", ROOT / "scripts/phase3h_shadow.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "OPERATIONAL_DIR", tmp_path)
    for directory in ("raw", "normalized", "manifests"):
        (tmp_path / directory).mkdir()
    frame = bars()
    frame["source_complete"] = True
    normalized = tmp_path / "normalized/IDX_NDX.csv"
    frame.to_csv(normalized, index=False)
    raw_bytes = b'{"synthetic_fixture":true}'
    digest = hashlib.sha256(raw_bytes).hexdigest()
    (tmp_path / "raw" / f"IDX_NDX_{digest}.json").write_bytes(raw_bytes)
    manifest = {"symbol": "^NDX", "frequency": "1d", "received_at": "2025-03-26T01:00:00+00:00",
                "raw_sha256": digest, "normalized_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest()}
    path = tmp_path / "manifests/IDX_NDX.json"
    path.write_text(json.dumps(manifest))
    now = datetime(2025, 3, 26, 2, tzinfo=UTC)
    assert len(runner.load_bars("^NDX", now)[0]) == len(frame)
    path.write_text(json.dumps({**manifest, "received_at": "2025-03-20T00:00:00+00:00"}))
    with pytest.raises(ValueError, match="stale"):
        runner.load_bars("^NDX", now)
    path.write_text(json.dumps(manifest))
    normalized.write_bytes(normalized.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum"):
        runner.load_bars("^NDX", now)
