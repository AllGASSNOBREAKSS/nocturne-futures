"""Explicit local snapshot/restore drill; never starts services or providers."""
import argparse
from datetime import datetime, timezone
import json
import re
import time
import os
import subprocess
from pathlib import Path

from nocturne.research.recovery import snapshot_evidence, restore_snapshot, verify_relocated_evidence

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-prefix", default="phase3p_recovery")
    sub = parser.add_subparsers(dest="mode", required=True)
    create = sub.add_parser("snapshot")
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--max-bytes", type=int, default=1024**3)
    create.add_argument("--max-seconds", type=int, default=30)
    check = sub.add_parser("check")
    check.add_argument("--snapshot", type=Path, required=True)
    check.add_argument("--restore-to", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.report_prefix):
        parser.error("report prefix must be a plain filename stem")
    started_at = datetime.now(timezone.utc)
    clock = time.monotonic()
    admission = None
    if args.mode == "snapshot":
        if os.name == 'nt':
            from nocturne.runtime_integrity import check_capture_window
            query = "$ErrorActionPreference='Stop'; $names=@('Nocturne-NDX-ReadOnly-Shadow','Nocturne-ReadOnly-Research'); $dates=@(Get-ScheduledTask | Where-Object { $_.TaskName -in $names -and $_.State -ne 'Disabled' } | ForEach-Object { ($_ | Get-ScheduledTaskInfo).NextRunTime.ToUniversalTime().ToString('o') }); ConvertTo-Json -InputObject $dates"
            dates = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query],
                                                      text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW))
            admission = check_capture_window(datetime.now(timezone.utc), dates, args.max_seconds)
        result = snapshot_evidence(ROOT, args.destination, args.max_bytes, args.max_seconds)
    else:
        restore_snapshot(args.snapshot, args.restore_to)
        result = verify_relocated_evidence(args.restore_to)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode, "result": result,
              "started_at": started_at.isoformat(), "elapsed_seconds": time.monotonic() - clock,
              "capture_admission": admission,
              "scope": "authorized local recovery drill; private archive not uploaded, not encrypted by this tool",
              "live_trading": "DISABLED"}
    path = ROOT / f"reports/{args.report_prefix}_{args.mode}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
