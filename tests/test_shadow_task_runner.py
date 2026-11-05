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
