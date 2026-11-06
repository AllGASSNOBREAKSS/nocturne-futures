"""Console-free Windows transport for the existing PowerShell task runners.

Standard library only: bootstrap failures must be recorded before package imports.
This does not schedule, train, issue forecasts or change Windows security policy.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def event(path, name, **detail):
    record = {"at": datetime.now(timezone.utc).isoformat(), "event": name, "pid": os.getpid(), **detail}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("shadow", "research"), required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows only; use existing CLI runners on other platforms")
    budget = 1140 if args.lane == "shadow" else 1020
    timeout = budget if args.timeout_seconds is None else args.timeout_seconds
    if not 1 <= timeout <= budget:
        parser.error("timeout must fit within the existing scheduled task limit")
    root = args.repository.resolve()
    logs = root / ("data/shadow/task-logs" if args.lane == "shadow" else "data/research/orchestrator/task-logs")
    logs.mkdir(parents=True, exist_ok=True)
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"-{os.getpid()}-launcher"
    journal = logs / f"{run}.jsonl"
    import ctypes
    event(journal, "LAUNCHER_STARTED", lane=args.lane, console_window=bool(ctypes.windll.kernel32.GetConsoleWindow()))
    code = 1
    process = None
    try:
        powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        runner = root / "scripts" / f"run_{args.lane}_task.ps1"
        if not args.python.is_file() or not runner.is_file():
            raise FileNotFoundError("runner/interpreter missing")
        with (logs / f"{run}.out.log").open("xb") as stdout, (logs / f"{run}.err.log").open("xb") as stderr:
            process = subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-File", str(runner),
                                        "-Python", str(args.python.resolve()), "-Repository", str(root)], cwd=root,
                                       stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            event(journal, "RUNNER_STARTED", child_pid=process.pid, creation="CREATE_NO_WINDOW")
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                event(journal, "RUNNER_TIMEOUT", timeout_seconds=timeout)
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                               stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
                process.wait(timeout=15)
                code = 124
    except Exception as exc:
        event(journal, "LAUNCHER_ERROR", error_type=type(exc).__name__)
        code = 1
    event(journal, "LAUNCHER_FINISHED", exit_code=code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
