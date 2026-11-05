"""Single allowlisted job subprocess; no training runs in the shadow process."""
import json
from pathlib import Path
import sys
import os
import traceback
import threading
import subprocess
import signal

from ..shadow.locking import FileLock
from .orchestrator import JobStore


def terminate_tree():
    """Watchdog also bounds a child whose runner has died."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(os.getpid()), "/T", "/F"], capture_output=True)
        os._exit(124)
    else:
        os.killpg(os.getpgrp(), signal.SIGKILL)


def main():
    state, identifier, attempt, repository = sys.argv[1:]
    store = JobStore(state)
    job = next(j for j in store.jobs() if j["id"] == identifier)
    lock = FileLock(store.root / f"{job['lane']}.active.lock")
    if not lock.acquire(blocking=False):
        return 2
    watchdog = threading.Timer(job["timeout"] + 5, terminate_tree)
    watchdog.daemon = True
    watchdog.start()
    try:
        if job["lane"] == "research" and os.name != "nt":
            os.nice(10)
        current = next(j for j in store.jobs() if j["id"] == identifier)
        if current["state"] != "RUNNING" or current["attempts"] != int(attempt):
            return 3
        from .jobs import execute_job
        directory = store.root / "attempts" / identifier / attempt
        print(f"START kind={job['kind']} job={identifier} attempt={attempt}", flush=True)
        try:
            result = execute_job(job["kind"], json.loads(job["payload"]), Path(repository), directory, store, job)
        except Exception as exc:
            # Keep provider URLs/credentials out of status; traceback is not emitted.
            result = {"status": "FAILED", "reason": type(exc).__name__}
            print(type(exc).__name__, file=sys.stderr)
            for frame in traceback.extract_tb(exc.__traceback__):
                print(f"  {Path(frame.filename).name}:{frame.lineno} {frame.name}", file=sys.stderr)
        result.update(job_id=identifier, kind=job["kind"], attempt=int(attempt), trading_decision="NO_TRADE")
        temp = directory / "result.tmp"
        with temp.open("w") as output:
            output.write(json.dumps(result, indent=2, default=str, allow_nan=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
        temp.replace(directory / "result.json")
        print(f"END status={result['status']}", flush=True)
        return 0
    finally:
        watchdog.cancel()
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
