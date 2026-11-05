import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from nocturne.shadow import ShadowStore
from nocturne.shadow.operations import assess_operations, monitor_operations

NOW = datetime(2026, 11, 4, 5, tzinfo=timezone.utc)


def good_status():
    return {"generated_at": NOW.isoformat(), "operational_status": "SHADOW_ACTIVE",
            "audit": {"failed": []}, "refresh": {"^NDX": {"status": "FETCHED"}}}


def test_incidents_are_deduplicated_resolved_and_reopened(tmp_path):
    store = ShadowStore(tmp_path)
    bad = {**good_status(), "operational_status": "DATA_BLOCKED"}
    assert len(monitor_operations(store, bad, NOW)["open_alerts"]) == 1
    assert monitor_operations(store, bad, NOW)["transitions_now"] == []
    good = monitor_operations(store, good_status(), NOW)
    assert good["open_alerts"] == []
    assert store.alert_events()[-1]["state"] == "RESOLVED"
    monitor_operations(store, bad, NOW)
    assert [e["state"] for e in store.alert_events()] == ["OPEN", "RESOLVED", "OPEN"]


def test_read_only_assessment_never_writes_alert_journal(tmp_path):
    store = ShadowStore(tmp_path)
    result = assess_operations(store, None, NOW)
    assert "NO_CYCLE_STATUS" in result["issues"]
    assert not store.alert_path.exists()


def test_stale_and_future_status_cannot_be_healthy(tmp_path):
    store = ShadowStore(tmp_path)
    for delta in (timedelta(hours=-2), timedelta(minutes=1)):
        result = assess_operations(store, {**good_status(), "generated_at": (NOW + delta).isoformat()}, NOW)
        assert "CYCLE_STATUS_STALE" in result["issues"]


def test_unavailable_status_does_not_claim_prior_alert_recovery(tmp_path):
    store = ShadowStore(tmp_path)
    failed = {**good_status(), "operational_status": "AUDIT_BLOCKED",
              "audit": {"failed": [{"forecast_id": "fixture", "issues": ["REFERENCE_CLOSE_MISMATCH"]}]}}
    monitor_operations(store, failed, NOW)
    result = monitor_operations(store, None, NOW)
    assert any(e["key"] == "FORECAST_AUDIT:fixture" for e in result["open_alerts"])
    assert not any(e["state"] == "RESOLVED" for e in store.alert_events())


def test_overdue_outcome_requires_real_elapsed_availability_and_grace(tmp_path):
    store = ShadowStore(tmp_path)
    store.append_forecast({"forecast_id": "fixture", "model_id": "ndx-range-v1", "target_date": "2026-11-04",
                           "data_date": "2026-11-03", "created_at": NOW.isoformat(),
                           "quantiles": {"p50": .01, "p80": .02, "p90": .03}, "features": {}, "feature_digest": "fixture"})
    assert assess_operations(store, good_status(), NOW)["overdue_outcomes"] == []
    later = NOW + timedelta(days=1, hours=1)
    result = assess_operations(store, {**good_status(), "generated_at": later.isoformat()}, later)
    assert result["overdue_outcomes"][0]["forecast_id"] == "fixture"
    assert store.outcomes() == []


def test_provider_failure_and_missed_deadline_are_alerted(tmp_path):
    store = ShadowStore(tmp_path)
    store.append_missed({"target_date": "2026-11-03", "recorded_at": NOW.isoformat(), "reason": "fixture"})
    status = {**good_status(), "refresh": {"^NDX": {"status": "FETCH_FAILED", "error_type": "Timeout"}}}
    issues = assess_operations(store, status, NOW)["issues"]
    assert "PROVIDER_REFRESH:^NDX" in issues
    assert "MISSED_ISSUANCE:2026-11-03" in issues


def test_one_shot_cycle_exception_is_durable_and_releases_lock(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("runner_alert_test", Path(__file__).resolve().parents[1] / "scripts/phase3h_shadow.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "STORE_DIR", tmp_path / "store")
    monkeypatch.setattr(runner, "LOCK_PATH", tmp_path / "run.lock")
    monkeypatch.setattr(runner, "STATUS_PATH", tmp_path / "status.json")
    def fail(*args):
        raise RuntimeError("sensitive-exception-message-not-for-logs")
    monkeypatch.setattr(runner, "load_bars", fail)
    result = runner.cycle(False, now=NOW)
    assert result["operational_status"] == "CYCLE_FAILED"
    assert "sensitive-exception" not in runner.STATUS_PATH.read_text()
    assert ShadowStore(tmp_path / "store").log_events()[-1]["event"] == "CYCLE_EXCEPTION"
    assert runner.acquire_lock()
    runner.release_lock()


def test_naive_monitor_time_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        assess_operations(ShadowStore(tmp_path), good_status(), datetime(2026, 11, 4))


@pytest.mark.parametrize("status", [["invalid"], {"audit": []}, {"generated_at": "not-a-timestamp"}])
def test_malformed_status_is_an_incident_not_false_recovery(tmp_path, status):
    result = monitor_operations(ShadowStore(tmp_path), status, NOW)
    assert result["status"] == "degraded"
    assert "CYCLE_STATUS_INVALID" in result["issues"]


def test_outcome_verification_is_fresh_and_bound_to_current_journals(tmp_path):
    import hashlib
    store = ShadowStore(tmp_path)
    store.forecast_path.write_text('{"forecast_id":"fixture"}\n')
    store.outcome_path.write_text('{"forecast_id":"fixture"}\n')
    proof = {"generated_at": NOW.isoformat(), "status": "AUDIT_BLOCKED", "verified": 0,
             "journal_hashes": {"forecasts": hashlib.sha256(store.forecast_path.read_bytes()).hexdigest(),
                                "outcomes": hashlib.sha256(store.outcome_path.read_bytes()).hexdigest()}}
    assert "OUTCOME_VERIFICATION_FAILED" in monitor_operations(store, good_status(), NOW, proof)["issues"]
    assert "OUTCOME_VERIFICATION_UNAVAILABLE" in monitor_operations(store, good_status(), NOW)["issues"]
    assert not any(e["state"] == "RESOLVED" for e in store.alert_events())
    valid = {**proof, "status": "VERIFIED_RESEARCH_GRADE", "verified": 1}
    assert monitor_operations(store, good_status(), NOW, valid)["open_alerts"] == []
    store.outcome_path.write_bytes(store.outcome_path.read_bytes() + b"\n")
    assert "OUTCOME_VERIFICATION_UNAVAILABLE" in assess_operations(store, good_status(), NOW, valid)["issues"]
