"""Bounded local evidence snapshots and offline relocation checks.

Not an off-host backup, encryption tool, service activator or billing operation.
Only trusted local evidence is supported; hashes are not digital signatures.
"""
from datetime import datetime, timezone, timedelta
from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sqlite3
import time

from ..adapters.snapshots import SnapshotStore, canonical, digest, immutable_write
from ..shadow.locking import FileLock

DIRECTORIES = ("data/shadow/market/snapshots", "models/shadow/ndx-range-v1",
               "data/history/yahoo_daily", "data/research/orchestrator",
               "data/licensed/databento", "data/licensed/databento_metadata")
JOURNALS = tuple("data/shadow/ndx_range/" + name for name in
                 ("forecasts.jsonl", "outcomes.jsonl", "reconciliations.jsonl", "alerts.jsonl",
                  "data_quality.jsonl", "missed.jsonl", "log.jsonl", "meta.json"))
LOCKS = ("data/research/orchestrator/research.runner.lock", "data/research/orchestrator/research.active.lock",
         "data/research/orchestrator/task-logs/task.wrapper.lock", "data/shadow/task-logs/task.wrapper.lock",
         "data/research/orchestrator/shadow.runner.lock", "data/research/orchestrator/shadow.active.lock",
         "data/shadow/ndx_range/run.lock", "data/shadow/ndx_range/.store.lock",
         "data/shadow/market/snapshots/archive.lock")
DATABASE = "data/research/orchestrator/jobs.sqlite"


def file_digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            checksum.update(chunk)
    return checksum.hexdigest()


def safe_path(root, name):
    part = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or part.is_absolute() or any(p in ("..", ".") for p in name.split("/")):
        raise ValueError("unsafe recovery path")
    path = root.joinpath(*part.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("recovery path escapes root")
    for parent in (path, *path.parents):
        if parent == root.parent:
            break
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            raise ValueError("linked recovery paths are unsupported")
    return path


def allowed(name):
    return name in JOURNALS or any(name.startswith(directory + "/") for directory in DIRECTORIES)


def db_rows(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        db.row_factory = sqlite3.Row
        return {table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY {order}")]
                for table, order in (("jobs", "id"), ("events", "seq"))}


def snapshot_evidence(project, destination, max_bytes=1024**3, max_seconds=30, now=None):
    from ..market_clock import ET, is_trading_day
    from ..shadow.calendar import supported
    from ..shadow.service import session_open
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware snapshot time required")
    day = now.astimezone(ET).date()
    if supported(day) and is_trading_day(day) and timedelta(0) <= session_open(day) - now <= timedelta(minutes=30):
        raise BlockingIOError("snapshot prohibited near the live issuance deadline")
    project, destination = Path(project).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError("recovery destination must be new; never overwrite a prior snapshot")
    if type(max_bytes) is not int or not 1 <= max_bytes <= 10 * 1024**3 or not 1 <= max_seconds <= 120:
        raise ValueError("invalid local snapshot budget")
    if destination == project or any(destination.is_relative_to(project / scope) for scope in DIRECTORIES):
        raise ValueError("destination overlaps captured evidence")
    held = []
    try:
        for name in LOCKS:
            lock = FileLock(project / name)
            if not lock.acquire(blocking=False):
                raise BlockingIOError("evidence producer active; retry at a non-critical time")
            held.append(lock)
        started = time.monotonic()
        paths = {project / name for name in JOURNALS if (project / name).exists()}
        for directory in DIRECTORIES:
            parent = project / directory
            if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
                raise ValueError("linked evidence root")
            if parent.exists():
                paths.update(path for path in parent.rglob("*") if path.is_file())
        paths = sorted(p for p in paths if not p.name.endswith((".lock", ".tmp", ".sqlite-wal", ".sqlite-shm", ".sqlite-journal")))
        if sum(path.stat().st_size for path in paths) > max_bytes:
            raise ValueError("local snapshot byte budget exceeded")
        destination.mkdir(parents=True)
        entries, total = [], 0
        for source in paths:
            name = source.relative_to(project).as_posix()
            safe_path(project, name)
            target = safe_path(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if time.monotonic() - started > max_seconds:
                raise TimeoutError("snapshot wall-clock budget; incomplete directory retained")
            if name == DATABASE:
                # SQLite backup API includes committed WAL contents; copying a
                # live database file directly would not provide this guarantee.
                with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as incoming:
                    with closing(sqlite3.connect(target)) as outgoing:
                        page_size = incoming.execute("PRAGMA page_size").fetchone()[0]
                        def progress(status, remaining, pages):
                            if total + pages * page_size > max_bytes or time.monotonic() - started > max_seconds:
                                raise TimeoutError("SQLite snapshot resource budget")
                        incoming.backup(outgoing, pages=32, progress=progress)
                        outgoing.commit()
                        outgoing.execute("PRAGMA journal_mode=DELETE").fetchone()
                total += target.stat().st_size
            else:
                with source.open("rb") as incoming, target.open("xb") as outgoing:
                    while chunk := incoming.read(65536):
                        if total + len(chunk) > max_bytes or time.monotonic() - started > max_seconds:
                            raise TimeoutError("snapshot resource budget; incomplete directory retained")
                        outgoing.write(chunk)
                        total += len(chunk)
            entries.append({"path": name, "bytes": target.stat().st_size, "sha256": file_digest(target),
                            "kind": "sqlite-backup" if name == DATABASE else "exact-bytes"})
        # Detect unsupported concurrent manual writers rather than certifying
        # their partially captured files. Scheduled writers honor the locks above.
        for entry in entries:
            source = safe_path(project, entry["path"])
            if entry["kind"] == "exact-bytes" and file_digest(source) != entry["sha256"]:
                raise ValueError("source changed during snapshot; incomplete directory retained")
        if (destination / DATABASE).exists() and db_rows(project / DATABASE) != db_rows(destination / DATABASE):
            raise ValueError("research database changed during snapshot")
        if sum(e["bytes"] for e in entries) > max_bytes or time.monotonic() - started > max_seconds:
            raise TimeoutError("snapshot final resource check failed")
        manifest = {"schema": 1, "source_root": str(project), "created_at": datetime.now(timezone.utc).isoformat(),
                    "verifier_sha256": digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
                    "scope": "private evidence and research state; not runnable service configuration",
                    "files": entries, "sqlite_logical_sha256": digest(canonical(db_rows(destination / DATABASE))) if (destination / DATABASE).exists() else None}
        body = canonical(manifest)
        immutable_write(destination / "manifest.json", body)
        immutable_write(destination / "manifest.sha256", digest(body).encode())
        return {"files": len(entries), "bytes": sum(e["bytes"] for e in entries), "manifest_sha256": digest(body)}
    finally:
        for lock in reversed(held):
            lock.release()


def verify_files(root):
    root = Path(root).resolve()
    body = (root / "manifest.json").read_bytes()
    if digest(body) != (root / "manifest.sha256").read_text().strip():
        raise ValueError("recovery manifest checksum mismatch")
    manifest = json.loads(body)
    names = set()
    for entry in manifest["files"]:
        name = entry["path"]
        if not allowed(name) or name in names:
            raise ValueError("unexpected or duplicate recovery scope")
        names.add(name)
        path = safe_path(root, name)
        if path.stat().st_size != entry["bytes"] or file_digest(path) != entry["sha256"]:
            raise ValueError("recovery file checksum mismatch")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != names | {"manifest.json", "manifest.sha256"}:
        raise ValueError("unmanifested or missing recovery files")
    if manifest["sqlite_logical_sha256"] is not None and digest(canonical(db_rows(root / DATABASE))) != manifest["sqlite_logical_sha256"]:
        raise ValueError("restored logical SQLite state changed")
    return manifest


def relocated(root, source_root, original):
    kind = PureWindowsPath if PureWindowsPath(source_root).drive else PurePosixPath
    try:
        relative = kind(original).relative_to(kind(source_root))
    except ValueError as exc:
        raise ValueError("recorded artifact is outside captured project") from exc
    name = PurePosixPath(*relative.parts).as_posix()
    if not allowed(name):
        raise ValueError("artifact is outside recovery scope")
    return safe_path(Path(root), name)


def verify_relocated_evidence(root):
    """Offline proof audit and deliberate reproduction, never forecast issuance."""
    from ..shadow import ShadowStore, audit_forecasts, load_artifact
    from ..shadow.outcome_audit import audit_outcomes
    from .daily_experiment import context_backtest
    import pandas as pd
    root = Path(root).resolve()
    manifest = verify_files(root)
    if manifest["verifier_sha256"] != digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")):
        raise ValueError("recovery verifier version differs; use reviewed matching code")
    store = ShadowStore(root / "data/shadow/ndx_range")
    artifact = load_artifact(root / "models/shadow", "ndx-range-v1")
    archive = SnapshotStore(root / "data/shadow/market/snapshots")
    head = json.loads((archive.root / "heads" / (digest(b"^NDX") + ".json")).read_text())
    audit = audit_forecasts(store, archive.frame(head["snapshot_id"]), snapshot_root=archive.root)
    outcomes = audit_outcomes(store, archive, artifact.metadata["baseline_quantiles"])
    if audit["failed"] or outcomes["status"] == "AUDIT_BLOCKED":
        raise ValueError("relocated shadow evidence failed its original audit gates")
    reproduced = []
    cached_models = 0
    if (root / DATABASE).exists():
        jobs = db_rows(root / DATABASE)["jobs"]
        for job in jobs:
            if job["state"] != "SUCCEEDED":
                continue
            result = json.loads(job["result"]) or {}
            if job["kind"] == "FEATURE_BUILD":
                path = relocated(root, manifest["source_root"], result["dataset_path"])
                if digest(path.read_bytes()) != result["dataset_sha256"]:
                    raise ValueError("restored dataset digest mismatch")
            if job["kind"] == "MODEL_TRAINING":
                directory = relocated(root, manifest["source_root"], result["destination"])
                for split in result["splits"]:
                    if digest((directory / f"fold_{split['fold']}.joblib").read_bytes()) != split["model_sha256"]:
                        raise ValueError("restored challenger checksum mismatch")
                    cached_models += 1
            if job["kind"] == "HISTORICAL_BACKTEST" and result.get("report", {}).get("scope") == "NON_EXECUTABLE_INDEX_CONTEXT_NOT_NQ_ES_PNL":
                # Trace the original feature dependency without rewriting backed-
                # up absolute paths, and read only the relocated artifact.
                indexed = {r["id"]: r for r in jobs}
                features = [indexed[i] for i in json.loads(job["dependencies"]) if indexed[i]["kind"] == "FEATURE_BUILD"]
                if len(features) != 1:
                    raise ValueError("index diagnostic lacks a unique feature lineage")
                data = json.loads(features[0]["result"])
                path = relocated(root, manifest["source_root"], data["dataset_path"])
                actual = context_backtest(pd.read_csv(path))
                if canonical(actual) != canonical(result["report"]):
                    raise ValueError("restored fixed index diagnostic did not reproduce exactly")
                reproduced.append({"symbol": result["symbol"], "observations": data["rows"],
                                   "scope": actual["scope"], "net_mean_fraction_2bp": actual["sensitivity"]["2"]["net_mean_fraction"]})
    # Audit code must not modify any captured byte, including journals/database.
    verify_files(root)
    return {"status": "VERIFIED_LOCAL_RELOCATION", "issued": audit["forecasts"], "verified_matured": outcomes["verified"],
            "reproduced_index_diagnostics": reproduced, "cached_challenger_files_verified": cached_models,
            "new_models_trained": 0, "network_requests": 0, "trading_decision": "NO_TRADE",
            "limitations": "same-host offline relocation using installed code; not off-host durability, different-machine restore or service activation"}


def restore_snapshot(snapshot, destination):
    snapshot, destination = Path(snapshot).resolve(), Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(snapshot):
        raise ValueError("restore destination must be new and outside the snapshot")
    manifest = verify_files(snapshot)
    destination.mkdir(parents=True)
    import shutil
    for entry in manifest["files"]:
        source = safe_path(snapshot, entry["path"])
        target = safe_path(destination, entry["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in ("manifest.json", "manifest.sha256"):
        shutil.copyfile(snapshot / name, destination / name)
    verify_files(destination)
    return {"status": "RESTORED_NOT_ACTIVATED", "files": len(manifest["files"])}
