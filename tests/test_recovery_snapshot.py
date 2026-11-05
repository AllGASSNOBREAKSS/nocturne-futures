"""Recovery fixtures are isolated synthetic data, never live performance."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3

import pandas as pd
import pytest

from nocturne.adapters.snapshots import canonical, digest
from nocturne.research.orchestrator import JobStore
from nocturne.research.recovery import (snapshot_evidence, verify_files, restore_snapshot,
                                       verify_relocated_evidence, safe_path, db_rows, DATABASE)
from nocturne.shadow.locking import FileLock
from test_outcome_audit import matured_fixture
from test_daily_experiment import history
from nocturne.research.daily_experiment import build_dataset, context_backtest

ROOT = Path(__file__).resolve().parents[1]
SAFE_TIME = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)


def project_fixture(tmp_path):
    archive, store, _ = matured_fixture(tmp_path / "inputs")
    root = tmp_path / "SYNTHETIC_PROJECT"
    shutil.copytree(archive.root, root / "data/shadow/market/snapshots")
    shutil.copytree(store.root, root / "data/shadow/ndx_range")
    shutil.copytree(ROOT / "models/shadow/ndx-range-v1", root / "models/shadow/ndx-range-v1")
    jobs = JobStore(root / "data/research/orchestrator")
    feature = jobs.submit("FEATURE_BUILD", "research", "fixture", {"symbol": "^NDX"})
    path = jobs.root / "attempts/fixture/dataset.csv"
    path.parent.mkdir(parents=True)
    build_dataset(history(100)).to_csv(path, index=False, lineterminator="\n")
    jobs.transition(feature, "SUCCEEDED", {"dataset_path": str(path), "dataset_sha256": digest(path.read_bytes()), "rows": len(pd.read_csv(path))})
    backtest = jobs.submit("HISTORICAL_BACKTEST", "research", "fixture", dependencies=[feature])
    jobs.transition(backtest, "SUCCEEDED", {"symbol": "^NDX", "report": context_backtest(pd.read_csv(path))})
    return root


def test_relocated_snapshot_verifies_proofs_and_exact_fixed_backtest_without_activation(tmp_path):
    root = project_fixture(tmp_path)
    original = (root / "data/shadow/ndx_range/forecasts.jsonl").read_bytes()
    snapshot = tmp_path / "snapshot"
    snapshot_evidence(root, snapshot, now=SAFE_TIME)
    # The embedded original absolute paths must no longer resolve: otherwise a
    # supposed relocation check could accidentally read the live originals.
    root = root.rename(tmp_path / "UNAVAILABLE_ORIGINAL_LOCATION")
    restored = tmp_path / "different_location"
    restore_snapshot(snapshot, restored)
    result = verify_relocated_evidence(restored)
    assert result["issued"] == result["verified_matured"] == 1
    assert len(result["reproduced_index_diagnostics"]) == 1
    assert result["new_models_trained"] == result["network_requests"] == 0
    assert (root / "data/shadow/ndx_range/forecasts.jsonl").read_bytes() == original
    assert (restored / "data/shadow/ndx_range/forecasts.jsonl").read_bytes() == original


def test_sqlite_backup_includes_committed_wal_without_copying_wal_files(tmp_path):
    root = project_fixture(tmp_path)
    with sqlite3.connect(root / DATABASE) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("INSERT INTO events(job_id,at,state,detail) VALUES('fixture',1,'TEST','WAL_MARKER')")
        connection.commit()
        snapshot_evidence(root, tmp_path / "snapshot", now=SAFE_TIME)
    rows = db_rows(tmp_path / "snapshot" / DATABASE)
    assert any(row["detail"] == "WAL_MARKER" for row in rows["events"])
    assert not list((tmp_path / "snapshot").rglob("*-wal"))


def test_busy_producer_and_deadline_do_not_get_interrupted_by_backup(tmp_path):
    root = project_fixture(tmp_path)
    with FileLock(root / "data/shadow/ndx_range/run.lock"):
        with pytest.raises(BlockingIOError):
            snapshot_evidence(root, tmp_path / "busy", now=SAFE_TIME)
    assert not (tmp_path / "busy").exists()
    with pytest.raises(BlockingIOError, match="deadline"):
        snapshot_evidence(root, tmp_path / "deadline", now=datetime(2026, 11, 5, 14, 20, tzinfo=timezone.utc))


def test_budget_and_existing_destination_cannot_overwrite_evidence(tmp_path):
    root = project_fixture(tmp_path)
    with pytest.raises(ValueError, match="byte budget"):
        snapshot_evidence(root, tmp_path / "small", max_bytes=1, now=SAFE_TIME)
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "user.txt").write_text("preserve")
    with pytest.raises(ValueError, match="new"):
        snapshot_evidence(root, destination, now=SAFE_TIME)
    assert (destination / "user.txt").read_text() == "preserve"


def test_corrupt_file_and_path_escape_fail_before_model_loading(tmp_path):
    root = project_fixture(tmp_path)
    snapshot = tmp_path / "snapshot"
    snapshot_evidence(root, snapshot, now=SAFE_TIME)
    path = snapshot / "data/shadow/ndx_range/forecasts.jsonl"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_files(snapshot)
    for name in ("../outside", "/absolute", "data/shadow/market/snapshots/../../escape", "C:/escape"):
        with pytest.raises(ValueError):
            safe_path(snapshot, name)


def test_manifest_scope_and_duplicate_entries_are_not_trusted(tmp_path):
    root = project_fixture(tmp_path)
    snapshot = tmp_path / "snapshot"
    snapshot_evidence(root, snapshot, now=SAFE_TIME)
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    manifest["files"].append(dict(manifest["files"][0]))
    body = canonical(manifest)
    (snapshot / "manifest.json").write_bytes(body)
    (snapshot / "manifest.sha256").write_text(digest(body))
    with pytest.raises(ValueError, match="duplicate"):
        verify_files(snapshot)


def test_unmanifested_files_and_wrong_verifier_version_block(tmp_path):
    root = project_fixture(tmp_path)
    snapshot = tmp_path / "snapshot"
    snapshot_evidence(root, snapshot, now=SAFE_TIME)
    unexpected = snapshot / "unexpected.txt"
    unexpected.write_text("not captured")
    with pytest.raises(ValueError, match="unmanifested"):
        verify_files(snapshot)
    unexpected.unlink()  # Only the deliberately created isolated test file.
    manifest = json.loads((snapshot / "manifest.json").read_bytes())
    manifest["verifier_sha256"] = "0" * 64
    body = canonical(manifest)
    (snapshot / "manifest.json").write_bytes(body)
    (snapshot / "manifest.sha256").write_text(digest(body))
    with pytest.raises(ValueError, match="verifier version"):
        verify_relocated_evidence(snapshot)
