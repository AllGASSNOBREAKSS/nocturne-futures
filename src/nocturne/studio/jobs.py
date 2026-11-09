"""Studio job service on the existing durable orchestrator.

Jobs live in their own store (data/studio/jobs) so user-launched work never
contends with scheduled research. A background thread drives the existing
`run_lane`, which executes each job in the allow-listed worker subprocess with
its watchdog, timeout and crash recovery. Jobs survive closing the UI; if the
app exits mid-job, the next start records the interruption honestly.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..research.orchestrator import JobStore, run_lane
from . import ROOT, STATE, atomic_write, read_json

KINDS = {"training": "STUDIO_TRAINING", "backtest": "STUDIO_BACKTEST", "sweep": "STUDIO_SWEEP"}
STORE_ROOT = STATE / "jobs"
CANCEL = STORE_ROOT / "cancel"


def store():
    STORE_ROOT.mkdir(parents=True, exist_ok=True)
    return JobStore(STORE_ROOT)


def submit(kind, config):
    from . import backtest, sweep, training
    errors = {"training": training.validate, "backtest": backtest.validate, "sweep": sweep.validate}[kind](config)
    if errors:
        return {"status": "REJECTED", "errors": errors}
    payload = {**config, "submitted_at": datetime.now(timezone.utc).isoformat()}
    identifier = store().submit(KINDS[kind], "research", uuid.uuid4().hex, payload, timeout=1800, max_attempts=1)  # orchestrator ceiling
    return {"status": "QUEUED", "job_id": identifier}


def _attempt_dir(job):
    return STORE_ROOT / "attempts" / job["id"] / str(job["attempts"]) if job["attempts"] else None


def describe(job, detail=False):
    payload = json.loads(job["payload"])
    out = {"job_id": job["id"], "kind": job["kind"], "state": job["state"], "attempts": job["attempts"],
           "created": datetime.fromtimestamp(job["created"], timezone.utc).isoformat(),
           "updated": datetime.fromtimestamp(job["updated"], timezone.utc).isoformat(),
           "name": payload.get("name"), "config": payload, "result": json.loads(job["result"]) if job["result"] else None}
    directory = _attempt_dir(job)
    if directory and (directory / "progress.json").exists():
        out["progress"] = read_json(directory / "progress.json")
    if detail and directory:
        for name in ("progress.log", "stdout.log", "stderr.log"):
            path = directory / name
            out.setdefault("logs", {})[name] = path.read_text(errors="replace")[-20000:] if path.exists() else ""
        out["report"] = read_json(directory / "report.json")
    return out


def list_jobs(kind=None):
    jobs = [j for j in store().jobs("research") if kind is None or j["kind"] == KINDS[kind]]
    return [describe(j) for j in sorted(jobs, key=lambda j: -j["created"])]


def get(identifier, detail=True):
    job = next((j for j in store().jobs("research") if j["id"] == identifier), None)
    return describe(job, detail) if job else None


def cancel(identifier):
    s = store()
    job = next((j for j in s.jobs("research") if j["id"] == identifier), None)
    if job is None:
        return {"status": "NOT_FOUND"}
    if job["state"] in ("QUEUED", "RETRY_WAIT"):
        s.transition(identifier, "DISABLED", {"status": "FAILED", "reason": "CANCELLED_BEFORE_START"})
        return {"status": "CANCELLED"}
    if job["state"] == "RUNNING":
        CANCEL.mkdir(parents=True, exist_ok=True)
        (CANCEL / identifier).write_text("cancel")
        return {"status": "CANCEL_REQUESTED"}
    return {"status": "ALREADY_FINISHED", "state": job["state"]}


def execute(kind, payload, directory):
    """Called inside the worker subprocess by research.jobs.execute_job."""
    from . import backtest, sweep, training
    directory = Path(directory)
    identifier = directory.parent.name
    log = directory / "progress.log"

    def progress(pct, message):
        record = {"percent": pct, "message": message, "at": datetime.now(timezone.utc).isoformat()}
        atomic_write(directory / "progress.json", json.dumps(record))
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{record['at']} [{pct:3d}%] {message}\n")

    cancelled = lambda: (CANCEL / identifier).exists()
    config = {k: v for k, v in payload.items() if k != "submitted_at"}
    try:
        runner = {"STUDIO_TRAINING": training.run, "STUDIO_BACKTEST": backtest.run, "STUDIO_SWEEP": sweep.run}[kind]
        return runner(config, directory, progress, cancelled)
    except backtest.Cancelled:
        progress(100, "cancelled by user")
        return {"status": "FAILED", "reason": "CANCELLED_BY_USER"}


class Worker(threading.Thread):
    def __init__(self, interval=2.0):
        super().__init__(daemon=True, name="studio-worker")
        self.interval, self.stopped = interval, threading.Event()
        self.last = None

    def run(self):
        while not self.stopped.is_set():
            try:
                self.last = run_lane(store(), ROOT, "research", max_jobs=1, budget_seconds=3600, backoff_seconds=5)
            except Exception as exc:  # keep serving; record the failure kind only
                self.last = {"status": "WORKER_ERROR", "reason": type(exc).__name__}
            self.stopped.wait(self.interval)
