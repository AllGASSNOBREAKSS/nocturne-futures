"""Real windowless subprocesses; synthetic scripts, never live forecasts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows windowless launcher")
@pytest.mark.parametrize("code,delay,timeout,expected", [(0, 0, 20, 0), (7, 0, 20, 7), (0, 10, 2, 124)])
def test_windowless_launcher_preserves_exit_codes_and_bounds_timeout(tmp_path, code, delay, timeout, expected):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("run_research_task.ps1", "task_events.ps1"):
        shutil.copyfile(ROOT / "scripts" / name, scripts / name)
    (scripts / "phase3m_research.py").write_text(f"import time\nprint('fixture only', flush=True)\ntime.sleep({delay})\nraise SystemExit({code})\n")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    command = [str(pythonw), str(ROOT / "scripts/run_headless_task.py"), "--lane", "research",
               "--python", sys.executable, "--repository", str(tmp_path), "--timeout-seconds", str(timeout)]
    result = subprocess.run(command, capture_output=True, timeout=40)
    assert result.returncode == expected, result.stderr
    logs = tmp_path / "data/research/orchestrator/task-logs"
    events = [json.loads(line) for line in next(logs.glob("*-launcher.jsonl")).read_text().splitlines()]
    assert events[0]["event"] == "LAUNCHER_STARTED"
    assert events[0]["console_window"] is False
    assert events[-1]["event"] == "LAUNCHER_FINISHED"
    assert events[-1]["exit_code"] == expected
    assert any(e.get("creation") == "CREATE_NO_WINDOW" for e in events)
    if expected == 124:
        assert any(e["event"] == "RUNNER_TIMEOUT" for e in events)
        wrapper = [json.loads(line) for line in next(logs.glob("*-events.jsonl")).read_text().splitlines()]
        assert not any(e["Event"] == "RUN_FINISHED" for e in wrapper)
