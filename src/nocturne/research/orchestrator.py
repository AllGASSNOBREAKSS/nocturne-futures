"""Host-local durable DAG runner. Separate process/locks for shadow and research.

SQLite owns job state; immutable attempt directories own evidence. No arbitrary
shell commands, paid ingestion, automatic model promotion or broker operations.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager

from ..shadow.locking import FileLock

JOB_TYPES = ("DATA_REFRESH", "DATA_VALIDATION", "FEATURE_BUILD", "HISTORICAL_BACKTEST",
             "WALK_FORWARD_VALIDATION", "MODEL_TRAINING", "MODEL_EVALUATION", "SHADOW_FORECAST",
             "FORECAST_MATURITY_CHECK", "FORWARD_EVALUATION", "MODEL_DRIFT_MONITOR", "RESEARCH_REPORT",
             "FREE_DATA_COLLECTION", "FREE_DATA_EXPERIMENT")
TERMINAL = {"SUCCEEDED", "FAILED", "BLOCKED", "DEPENDENCY_FAILED", "DEPENDENCY_BLOCKED", "DISABLED"}
SHADOW_TYPES = {"DATA_REFRESH", "SHADOW_FORECAST", "FORECAST_MATURITY_CHECK", "FORWARD_EVALUATION", "MODEL_DRIFT_MONITOR"}


class JobStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, lane TEXT NOT NULL,
                payload TEXT NOT NULL, dependencies TEXT NOT NULL, state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
                timeout REAL NOT NULL, ready_at REAL NOT NULL DEFAULT 0,
                result TEXT, created REAL NOT NULL, updated REAL NOT NULL)''')
            db.execute('''CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, job_id TEXT, at REAL, state TEXT, detail TEXT)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / "jobs.sqlite", timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def submit(self, kind, lane, key, payload=None, dependencies=(), max_attempts=2, timeout=300):
        if kind not in JOB_TYPES or lane not in ("shadow", "research"):
            raise ValueError("unsupported job type/lane")
        if kind != "RESEARCH_REPORT" and ((kind in SHADOW_TYPES) != (lane == "shadow")):
            raise ValueError("inference and research job types must remain in their assigned lanes")
        if not 1 <= max_attempts <= 5 or not 1 <= timeout <= 1800:
            raise ValueError("resource/retry bounds exceeded")
        encoded = json.dumps(payload or {}, sort_keys=True)
        deps = json.dumps(list(dependencies))
        identifier = hashlib.sha256(f"{lane}|{kind}|{key}".encode()).hexdigest()[:24]
        with self.connect() as db:
            for dependency in dependencies:
                row = db.execute("SELECT lane FROM jobs WHERE id=?", (dependency,)).fetchone()
                if not row or row["lane"] != lane:
                    raise ValueError("dependencies must already exist in the same lane")
            old = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            if old and (old["payload"] != encoded or old["dependencies"] != deps
                        or old["max_attempts"] != max_attempts or old["timeout"] != timeout):
                raise ValueError("idempotency key reused with different specification")
            now = time.time()
            db.execute("INSERT OR IGNORE INTO jobs(id,kind,lane,payload,dependencies,state,max_attempts,timeout,created,updated) VALUES(?,?,?,?,?,'QUEUED',?,?,?,?)",
                       (identifier, kind, lane, encoded, deps, max_attempts, timeout, now, now))
            if not old and (payload or {}).get("enabled") is False:
                db.execute("UPDATE jobs SET state='DISABLED',result=? WHERE id=?", (json.dumps({"reason": "EXPLICITLY_DISABLED_BY_JOB_SPECIFICATION"}), identifier))
                db.execute("INSERT INTO events(job_id,at,state,detail) VALUES(?,?,'DISABLED',?)", (identifier, now, "explicit job specification"))
        return identifier

    def jobs(self, lane=None):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM jobs" + (" WHERE lane=?" if lane else "") + " ORDER BY created,id", (lane,) if lane else ()).fetchall()
        return [dict(r) for r in rows]

    def transition(self, identifier, state, result=None, ready_at=0):
        with self.connect() as db:
            now = time.time()
            db.execute("UPDATE jobs SET state=?,result=?,ready_at=?,updated=? WHERE id=?",
                       (state, json.dumps(result), ready_at, now, identifier))
            db.execute("INSERT INTO events(job_id,at,state,detail) VALUES(?,?,?,?)",
                       (identifier, now, state, json.dumps(result)))

    def events(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY seq")]


def run_lane(store, repository, lane, max_jobs=12, budget_seconds=900, backoff_seconds=30, only_ids=None):
    if lane not in ("research", "shadow") or not 1 <= max_jobs <= 100 or not 1 <= budget_seconds <= 3600:
        raise ValueError("invalid lane/budget")
    lock = FileLock(store.root / f"{lane}.runner.lock")
    if not lock.acquire(blocking=False):
        return {"status": "BUSY", "executed": 0}
    started, executed = time.monotonic(), 0
    try:
        # A child survives parent death. Never recover/requeue while it is active.
        active = FileLock(store.root / f"{lane}.active.lock")
        if not active.acquire(blocking=False):
            return {"status": "BUSY_CHILD", "executed": 0}
        active.release()
        for job in store.jobs(lane):
            if job["state"] == "RUNNING":
                directory = store.root / "attempts" / job["id"] / str(job["attempts"])
                result_path = directory / "result.json"
                if result_path.exists():
                    try:
                        result = json.loads(result_path.read_text())
                        if (not isinstance(result, dict) or result.get("job_id") != job["id"] or result.get("attempt") != job["attempts"]
                                or result.get("kind") != job["kind"] or result.get("status") not in ("SUCCEEDED", "FAILED", "BLOCKED")):
                            raise ValueError("recovery result identity mismatch")
                    except (OSError, ValueError, TypeError):
                        result = {"status": "FAILED", "reason": "INVALID_RECOVERY_RESULT"}
                    state = result["status"]
                    if state == "FAILED" and job["attempts"] < job["max_attempts"]:
                        state = "RETRY_WAIT"
                    store.transition(job["id"], state, result, time.time() + backoff_seconds)
                else:
                    state = "RETRY_WAIT" if job["attempts"] < job["max_attempts"] else "FAILED"
                    store.transition(job["id"], state, {"reason": "INTERRUPTED_PROCESS_RECOVERY"}, time.time() + backoff_seconds)
        while executed < max_jobs and time.monotonic() - started < budget_seconds:
            jobs = store.jobs(lane)
            states = {j["id"]: j["state"] for j in jobs}
            selected = None
            for job in jobs:
                if only_ids is not None and job["id"] not in only_ids:
                    continue
                if job["state"] not in ("QUEUED", "RETRY_WAIT") or job["ready_at"] > time.time():
                    continue
                dependencies = json.loads(job["dependencies"])
                if any(states[d] in TERMINAL - {"SUCCEEDED"} for d in dependencies):
                    failed = any(states[d] in {"FAILED", "DEPENDENCY_FAILED"} for d in dependencies)
                    store.transition(job["id"], "DEPENDENCY_FAILED" if failed else "DEPENDENCY_BLOCKED", {"dependencies": dependencies})
                    continue
                if all(states[d] == "SUCCEEDED" for d in dependencies):
                    selected = job
                    break
            if selected is None:
                break
            job = selected
            # Count reserved directories as consumed attempts after a crash
            # between directory creation and the durable RUNNING transition.
            existing = store.root / "attempts" / job["id"]
            reserved = max([int(p.name) for p in existing.glob("*") if p.is_dir() and p.name.isdigit()] or [0])
            attempt = max(job["attempts"], reserved) + 1
            if attempt > job["max_attempts"]:
                store.transition(job["id"], "FAILED", {"reason": "ATTEMPT_BUDGET_CONSUMED_BY_INTERRUPTION"})
                continue
            directory = store.root / "attempts" / job["id"] / str(attempt)
            directory.mkdir(parents=True, exist_ok=False)
            with store.connect() as db:
                db.execute("UPDATE jobs SET attempts=? WHERE id=?", (attempt, job["id"]))
            store.transition(job["id"], "RUNNING", {"attempt_directory": str(directory)})
            env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                   "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "7"}
            src = str(Path(repository).resolve() / "src")
            env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
            options = {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS} if os.name == "nt" and lane == "research" else {}
            if os.name != "nt":
                options["start_new_session"] = True
            limit = min(job["timeout"], max(1, budget_seconds - (time.monotonic() - started)))
            try:
                with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
                    process = subprocess.Popen([sys.executable, "-m", "nocturne.research.job_worker", str(store.root),
                                                job["id"], str(attempt), str(Path(repository).resolve())],
                                               cwd=repository, env=env, stdout=stdout, stderr=stderr, **options)
                    try:
                        code = process.wait(timeout=limit)
                    except subprocess.TimeoutExpired:
                        if os.name == "nt":
                            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                        else:
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise TimeoutError("job wall-clock limit")
                result = json.loads((directory / "result.json").read_text()) if code == 0 else {"status": "FAILED", "reason": "CHILD_PROCESS_FAILED", "exit_code": code}
                if not isinstance(result, dict) or (code == 0 and (
                    result.get("job_id") != job["id"] or result.get("kind") != job["kind"] or result.get("attempt") != attempt)):
                    raise ValueError("worker result identity mismatch")
            except (OSError, ValueError, TimeoutError) as exc:
                result = {"status": "FAILED", "reason": type(exc).__name__}
            state = result.get("status", "INVALID")
            if state not in ("SUCCEEDED", "FAILED", "BLOCKED"):
                state, result = "FAILED", {"reason": "INVALID_WORKER_RESULT"}
            if state == "FAILED" and attempt < job["max_attempts"]:
                state = "RETRY_WAIT"
            store.transition(job["id"], state, result, time.time() + backoff_seconds * 2 ** (attempt - 1))
            executed += 1
        return {"status": "COMPLETED_TICK", "executed": executed, "lane": lane}
    finally:
        lock.release()
