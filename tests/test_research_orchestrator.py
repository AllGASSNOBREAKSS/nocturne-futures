import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nocturne.research.orchestrator import JobStore, run_lane, JOB_TYPES, SHADOW_TYPES
from nocturne.shadow.locking import FileLock

ROOT = Path(__file__).resolve().parents[1]


def test_supported_jobs_and_idempotency_cannot_change_specification(tmp_path):
    store = JobStore(tmp_path)
    for kind in JOB_TYPES:
        lane = "shadow" if kind in SHADOW_TYPES else "research"
        first = store.submit(kind, lane, "fixed")
        assert first == store.submit(kind, lane, "fixed")
    with pytest.raises(ValueError, match="specification"):
        store.submit("FEATURE_BUILD", "research", "fixed", {"symbol": "changed"})
    with pytest.raises(ValueError):
        store.submit("ARBITRARY_SHELL", "research", "bad")


def test_dependencies_must_exist_and_cannot_tie_training_to_inference(tmp_path):
    store = JobStore(tmp_path)
    train = store.submit("MODEL_TRAINING", "research", "fixed")
    with pytest.raises(ValueError):
        store.submit("SHADOW_FORECAST", "shadow", "fixed", dependencies=[train])
    with pytest.raises(ValueError):
        store.submit("MODEL_TRAINING", "research", "other", dependencies=["missing"])
    with pytest.raises(ValueError, match="assigned lanes"):
        store.submit("MODEL_TRAINING", "shadow", "forbidden")


def test_real_child_failure_is_isolated_and_retry_is_bounded(tmp_path):
    store = JobStore(tmp_path / "state")
    # Missing dependency causes a real handler error; independent report still runs.
    failed = store.submit("FEATURE_BUILD", "research", "bad", {"symbol": "invalid"}, max_attempts=2)
    child = store.submit("MODEL_TRAINING", "research", "downstream", dependencies=[failed])
    independent = store.submit("RESEARCH_REPORT", "research", "independent")
    run_lane(store, ROOT, "research", backoff_seconds=0)
    states = {j["id"]: j for j in store.jobs()}
    assert states[failed]["state"] == "FAILED" and states[failed]["attempts"] == 2
    assert states[child]["state"] == "DEPENDENCY_FAILED"
    assert states[independent]["state"] == "SUCCEEDED"
    assert len(list((store.root / "attempts" / failed).glob("*/stderr.log"))) == 2
    run_lane(JobStore(store.root), ROOT, "research")
    assert {j["id"]: j for j in store.jobs()}[failed]["attempts"] == 2


def test_lane_lock_and_orphan_worker_prevent_duplicate_work(tmp_path):
    store = JobStore(tmp_path)
    lock = FileLock(tmp_path / "research.runner.lock")
    with lock:
        assert run_lane(store, ROOT, "research")["status"] == "BUSY"
    with FileLock(tmp_path / "research.active.lock"):
        assert run_lane(store, ROOT, "research")["status"] == "BUSY_CHILD"
        # Research activity has no lock dependency on the shadow lane.
        assert run_lane(store, ROOT, "shadow")["status"] == "COMPLETED_TICK"


def test_restart_recovers_committed_result_without_reexecuting(tmp_path):
    store = JobStore(tmp_path)
    identifier = store.submit("RESEARCH_REPORT", "research", "recovered")
    directory = tmp_path / "attempts" / identifier / "1"
    directory.mkdir(parents=True)
    (directory / "result.json").write_text(json.dumps({"status": "SUCCEEDED", "job_id": identifier, "attempt": 1,
                                                       "kind": "RESEARCH_REPORT", "proof": "completed before parent died"}))
    with store.connect() as db:
        db.execute("UPDATE jobs SET attempts=1,state='RUNNING' WHERE id=?", (identifier,))
    assert run_lane(store, ROOT, "research")["executed"] == 0
    assert store.jobs()[0]["state"] == "SUCCEEDED"


def test_interrupted_without_result_uses_retry_backoff(tmp_path):
    store = JobStore(tmp_path)
    identifier = store.submit("RESEARCH_REPORT", "research", "interrupted")
    with store.connect() as db:
        db.execute("UPDATE jobs SET attempts=1,state='RUNNING' WHERE id=?", (identifier,))
    run_lane(store, ROOT, "research", backoff_seconds=300)
    assert store.jobs()[0]["state"] == "RETRY_WAIT"
    assert store.jobs()[0]["attempts"] == 1


def test_job_count_budget_and_result_logs(tmp_path):
    store = JobStore(tmp_path)
    for n in range(3):
        store.submit("RESEARCH_REPORT", "research", str(n))
    assert run_lane(store, ROOT, "research", max_jobs=1)["executed"] == 1
    assert sum(j["state"] == "QUEUED" for j in store.jobs()) == 2
    assert next((tmp_path / "attempts").glob("*/*/stdout.log")).read_text().startswith("START")


def test_timeout_kills_child_and_does_not_mark_success(tmp_path):
    store = JobStore(tmp_path)
    store.submit("RESEARCH_REPORT", "research", "timeout", max_attempts=1)
    import subprocess
    with patch("nocturne.research.orchestrator.subprocess.Popen") as factory:
        factory.return_value.pid = 123456789
        factory.return_value.wait.side_effect = [subprocess.TimeoutExpired("fixture", 1), 0]
        with patch("nocturne.research.orchestrator.subprocess.run"), patch("nocturne.research.orchestrator.os.killpg", create=True):
            run_lane(store, ROOT, "research")
    assert store.jobs()[0]["state"] == "FAILED"
    assert json.loads(store.jobs()[0]["result"])["reason"] == "TimeoutError"


def test_crash_between_directory_reservation_and_state_update_is_bounded(tmp_path):
    store = JobStore(tmp_path)
    identifier = store.submit("RESEARCH_REPORT", "research", "reserved", max_attempts=1)
    (tmp_path / "attempts" / identifier / "1").mkdir(parents=True)
    run_lane(store, ROOT, "research")
    assert store.jobs()[0]["state"] == "FAILED"
    assert json.loads(store.jobs()[0]["result"])["reason"] == "ATTEMPT_BUDGET_CONSUMED_BY_INTERRUPTION"


def test_corrupted_recovery_result_cannot_be_success(tmp_path):
    store = JobStore(tmp_path)
    identifier = store.submit("RESEARCH_REPORT", "research", "corrupt", max_attempts=1)
    directory = tmp_path / "attempts" / identifier / "1"
    directory.mkdir(parents=True)
    (directory / "result.json").write_text('{"status": "SUCCEEDED"}')
    with store.connect() as db:
        db.execute("UPDATE jobs SET attempts=1,state='RUNNING' WHERE id=?", (identifier,))
    run_lane(store, ROOT, "research")
    assert store.jobs()[0]["state"] == "FAILED"


def test_watchdog_targets_worker_process_group_not_shadow(monkeypatch):
    import nocturne.research.job_worker as worker
    if worker.os.name == "nt":
        with patch.object(worker.subprocess, "run") as terminate, patch.object(worker.os, "_exit") as exit_call:
            worker.terminate_tree()
            args = terminate.call_args.args[0]
            assert args == ["taskkill", "/PID", str(worker.os.getpid()), "/T", "/F"]
            exit_call.assert_called_once_with(124)
    else:
        with patch.object(worker.os, "killpg") as terminate:
            worker.terminate_tree()
            terminate.assert_called_once_with(worker.os.getpgrp(), worker.signal.SIGKILL)
