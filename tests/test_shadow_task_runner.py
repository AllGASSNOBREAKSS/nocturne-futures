"""Real PowerShell execution, isolated fixture scripts and temporary logs only."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell task-runner contract")
@pytest.mark.parametrize("failing_stage", [None, "audit"])
def test_task_runner_keeps_all_stages_and_real_exit_codes(tmp_path, failing_stage):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    mapping = {"cycle": "phase3h_shadow.py", "audit": "phase3l_forward_audit.py",
               "report": "phase3i_forward_report.py", "monitor": "phase3j_operations.py", "health": "phase3o_health.py"}
    for stage, name in mapping.items():
        (scripts / name).write_text("import sys\nprint('fixture-stage')\nprint('fixture-warning', file=sys.stderr)\n"
                                   f"raise SystemExit({1 if stage == failing_stage else 0})\n")
    runner = Path(__file__).resolve().parents[1] / "scripts/run_shadow_task.ps1"
    result = subprocess.run(["powershell", "-NoProfile", "-File", str(runner),
                             "-Python", sys.executable, "-Repository", str(tmp_path)],
                            capture_output=True, timeout=60)
    assert result.returncode == (1 if failing_stage else 0)
    logs = tmp_path / "data/shadow/task-logs"
    stages = json.loads(next(logs.glob("*-stages.json")).read_text(encoding="utf-8-sig"))
    assert [s["Stage"] for s in stages] == list(mapping)
    assert [s["ExitCode"] for s in stages] == [1 if s == failing_stage else 0 for s in mapping]
    assert all(p.stat().st_size > 0 for p in logs.glob("*.out.log"))
    events = [json.loads(line) for line in next(logs.glob("*-events.jsonl")).read_text().splitlines()]
    assert events[0]["Event"] == "RUN_STARTED"
    assert events[-1]["Event"] == "RUN_FINISHED"
    assert events[-1]["Detail"]["ExitCode"] == result.returncode
    assert sum(e["Event"] == "STAGE_STARTED" for e in events) == 5


@pytest.mark.skipif(os.name != "nt", reason="Windows scheduled wrapper contracts")
@pytest.mark.parametrize("code", [0, 7])
def test_research_wrapper_preserves_failure_and_lifecycle(tmp_path, code):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "phase3m_research.py").write_text(f"print('fixture only')\nraise SystemExit({code})\n")
    runner = Path(__file__).resolve().parents[1] / "scripts/run_research_task.ps1"
    result = subprocess.run(["powershell", "-NoProfile", "-File", str(runner), "-Python", sys.executable,
                             "-Repository", str(tmp_path)], capture_output=True, timeout=30)
    assert result.returncode == code
    logs = tmp_path / "data/research/orchestrator/task-logs"
    events = [json.loads(line) for line in next(logs.glob("*-events.jsonl")).read_text().splitlines()]
    assert [e["Event"] for e in events] == ["RUN_STARTED", "RUN_FINISHED"]
    assert events[-1]["Detail"]["ExitCode"] == code


@pytest.mark.skipif(os.name != "nt", reason="Windows exclusive wrapper guard")
def test_overlap_is_nonzero_busy_and_os_releases_guard(tmp_path):
    import time
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "phase3m_research.py").write_text("import time\nprint('fixture only', flush=True)\ntime.sleep(4)\n")
    runner = Path(__file__).resolve().parents[1] / "scripts/run_research_task.ps1"
    command = ["powershell", "-NoProfile", "-File", str(runner), "-Python", sys.executable, "-Repository", str(tmp_path)]
    first = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        logs = tmp_path / "data/research/orchestrator/task-logs"
        deadline = time.monotonic() + 15
        while not list(logs.glob("*.out.log")) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert first.poll() is None
        overlap = subprocess.run(command, capture_output=True, timeout=20)
        assert overlap.returncode == 75
        assert first.wait(timeout=20) == 0
        # A later execution is allowed; the guard is not a persistent sentinel.
        assert subprocess.run(command, capture_output=True, timeout=20).returncode == 0
    finally:
        if first.poll() is None:
            subprocess.run(["taskkill", "/PID", str(first.pid), "/T", "/F"], capture_output=True)
