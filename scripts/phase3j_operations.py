"""Durable local operational alerts; safe to invoke from an external monitor."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from nocturne.shadow import ShadowStore
from nocturne.shadow.operations import monitor_operations
from nocturne.shadow.locking import FileLock

ROOT = Path(__file__).resolve().parents[1]


def main():
    store = ShadowStore(ROOT / "data/shadow/ndx_range")
    with FileLock(store.root / "monitor.lock"):
        try:
            status = json.loads((ROOT / "reports/phase3h_shadow_status.json").read_text())
        except (FileNotFoundError, ValueError):
            status = None
        report = monitor_operations(store, status, datetime.now(timezone.utc))
        destination = ROOT / "reports/phase3j_operations.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
    print(json.dumps({"status": report["status"], "open_alerts": len(report["open_alerts"]),
                      "issued": report["issued"], "matured": report["matured"]}))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
