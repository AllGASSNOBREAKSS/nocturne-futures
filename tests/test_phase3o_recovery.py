"""Synthetic recovery/integration evidence only; never market performance."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

from nocturne.adapters.snapshots import canonical, digest
from nocturne.adapters.yahoo_history import _frame
from nocturne.research.orchestrator import JobStore, run_lane
from nocturne.research.health import assess_jobs
from nocturne.shadow import audit_forecasts
from nocturne.shadow.operations import monitor_operations
from nocturne.shadow.reconciliation import investigate_revision, verify_reconciliation
from nocturne.shadow.service import health
from test_market_snapshots import evidence, capture

ROOT = Path(__file__).resolve().parents[1]


def test_reconciled_fixture_recovers_alerts_and_new_observation_blocks_again(tmp_path):
    archive, store, _, forecast = evidence(tmp_path)
    before = store.forecast_path.read_bytes()
    now = pd.Timestamp("2025-03-25T02:10Z").to_pydatetime()
    revised = capture(archive, revision=True, received="2025-03-25T02:00Z")
    frame = archive.frame(revised)
    bad_audit = audit_forecasts(store, frame, snapshot_root=archive.root)
    status = {"generated_at": now.isoformat(), "operational_status": "AUDIT_BLOCKED", "audit": bad_audit, "refresh": {}}
    assert monitor_operations(store, status, now)["open_alerts"]
    proof = investigate_revision(forecast, archive, revised, now)
    store.append_reconciliation(proof["record"])
    good_audit = audit_forecasts(store, frame, snapshot_root=archive.root)
    assert good_audit["failed"] == []
    recovered = monitor_operations(store, {**status, "operational_status": "SHADOW_ACTIVE", "audit": good_audit}, now)
    assert recovered["open_alerts"] == []
    assert any(e["state"] == "RESOLVED" for e in store.alert_events())
    changed = frame.copy()
    changed.loc[changed.index[-1], "volume"] += 1  # same close, different observation
    assert audit_forecasts(store, changed, snapshot_root=archive.root)["failed"]
    assert store.forecast_path.read_bytes() == before and not store.outcomes()


def test_investigation_refuses_changed_forecast_and_corrupt_archive(tmp_path):
    archive, _, _, forecast = evidence(tmp_path)
    revised = capture(archive, revision=True, received="2025-03-25T02:00Z")
    now = pd.Timestamp("2025-03-25T02:10Z")
    with pytest.raises(ValueError, match="sealed"):
        investigate_revision({**forecast, "reference_close": 1.}, archive, revised, now)
    m = archive.manifest(revised)
    archive._object(m["raw_sha256"]).write_bytes(b"broken fixture")
    with pytest.raises(ValueError):
        investigate_revision(forecast, archive, revised, now)


def test_recent_failure_cannot_be_hidden_by_earlier_success(tmp_path):
    from nocturne.shadow import ShadowStore
    now = datetime(2026, 11, 5, 20, tzinfo=timezone.utc)
    store = ShadowStore(tmp_path)
    store.log("CYCLE_OK", now=now - timedelta(hours=1))
    store.log("CYCLE_AUDIT_FAILED", now=now)
    state = health(store, now)
    assert state["status"] == "degraded"
    assert "LATEST_CYCLE_NOT_OK" in state["warnings"]
    assert state["last_attempt_event"] == "CYCLE_AUDIT_FAILED"


def test_blocked_and_disabled_dependencies_do_not_become_software_failures(tmp_path):
    store = JobStore(tmp_path)
    blocked = store.submit("HISTORICAL_BACKTEST", "research", "missing", {"scope": "raw_futures"})
    store.transition(blocked, "BLOCKED", {"reason": "AUTHENTIC_CONTRACT_HISTORY_REQUIRED"})
    child = store.submit("MODEL_TRAINING", "research", "wait-for-data", dependencies=[blocked])
    disabled = store.submit("MODEL_TRAINING", "research", "off", {"enabled": False})
    disabled_child = store.submit("MODEL_EVALUATION", "research", "off-child", dependencies=[disabled])
    run_lane(store, ROOT, "research")
    states = {j["id"]: j["state"] for j in store.jobs()}
    assert states[child] == "DEPENDENCY_BLOCKED" and states[disabled] == "DISABLED"
    assert states[disabled_child] == "DEPENDENCY_BLOCKED"
    assert not (tmp_path / "attempts").exists()
    result = assess_jobs(store.jobs(), datetime.now(timezone.utc))
    assert result["counts"] == {"BLOCKED": 3, "DISABLED": 1}


def test_provider_outage_and_integrity_block_have_distinct_component_reasons(tmp_path):
    from nocturne.shadow import ShadowStore
    from nocturne.shadow.operations import assess_operations
    now = datetime(2026, 11, 5, 20, tzinfo=timezone.utc)
    status = {"generated_at": now.isoformat(), "operational_status": "DATA_BLOCKED", "audit": {"failed": []},
              "refresh": {"^NDX": {"status": "FETCH_FAILED", "error_type": "Timeout"}}}
    report = assess_operations(ShadowStore(tmp_path), status, now)
    assert report["components"]["shadow_cycle"]["status"] == "BLOCKED"
    assert report["components"]["provider_refresh"]["status"] == "FAILED"
    assert "PROVIDER_REFRESH:^NDX" in report["issues"]


def test_fixture_end_to_end_real_worker_dag_is_reproducible_and_isolated(tmp_path):
    from test_daily_experiment import history
    project = tmp_path / "SYNTHETIC_ONLY_PROJECT"
    data_root = project / "data/history/yahoo_daily"
    for subdir in ("raw", "normalized", "manifests"):
        (data_root / subdir).mkdir(parents=True)
    for symbol in ("^NDX", "^GSPC"):
        bars = history()
        raw = canonical({"chart": {"result": [{"meta": {"symbol": symbol},
                "timestamp": [int(s.timestamp()) for s in bars.timestamp],
                "indicators": {"quote": [{key: bars[key].tolist() for key in ("open", "high", "low", "close", "volume")}]}}]}})
        value = _frame(json.loads(raw), symbol)
        normalized = value.to_csv(index=False, lineterminator="\n").encode()
        name = symbol.replace("^", "IDX_")
        (data_root / "raw" / f"{name}_{digest(raw)}.json").write_bytes(raw)
        (data_root / "normalized" / f"{name}.csv").write_bytes(normalized)
        (data_root / "manifests" / f"{name}.json").write_text(json.dumps({"symbol": symbol, "rows": len(value),
            "raw_sha256": digest(raw), "normalized_sha256": digest(normalized), "kind": "SYNTHETIC_FIXTURE_NOT_MARKET", "license_scope": "TEST_ONLY"}))
    for name in ("src/nocturne/research/daily_experiment.py", "src/nocturne/research/validation.py", "src/nocturne/ml/calibration.py"):
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    (project / "reports").mkdir()
    store = JobStore(tmp_path / "fixture_jobs")
    validation = store.submit("DATA_VALIDATION", "research", "fixture")
    feature = store.submit("FEATURE_BUILD", "research", "fixture", {"symbol": "^NDX"}, [validation])
    backtest = store.submit("HISTORICAL_BACKTEST", "research", "fixture", dependencies=[feature])
    split = store.submit("WALK_FORWARD_VALIDATION", "research", "fixture", dependencies=[feature])
    train = store.submit("MODEL_TRAINING", "research", "fixture", dependencies=[split])
    evaluate = store.submit("MODEL_EVALUATION", "research", "fixture", dependencies=[train])
    report = store.submit("RESEARCH_REPORT", "research", "fixture", dependencies=[backtest, evaluate])
    result = run_lane(store, project, "research", budget_seconds=180)
    assert result["executed"] == 7
    assert {j["state"] for j in store.jobs()} == {"SUCCEEDED"}, store.jobs()
    scored = json.loads(next(j for j in store.jobs() if j["id"] == evaluate)["result"])
    assert scored["evaluation"]["holdout_scored"] is False
    assert scored["evaluation"]["decision"] == "NO_PROMOTION"
    assert run_lane(JobStore(store.root), project, "research")["executed"] == 0
    assert not (project / "data/shadow").exists()
