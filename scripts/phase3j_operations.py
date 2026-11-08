"""Durable local operational alerts; safe to invoke from an external monitor."""
import json
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from nocturne.shadow import ShadowStore
from nocturne.shadow.operations import monitor_operations
from nocturne.shadow.locking import FileLock

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ack-alert', help='existing open alert key; acknowledgement does not resolve it')
    parser.add_argument('--actor', help='bounded operator identifier, never a secret')
    parser.add_argument('--reason-code', help='uppercase reason code, no free-form text or secrets')
    args = parser.parse_args()
    if any((args.ack_alert, args.actor, args.reason_code)) and not all((args.ack_alert, args.actor, args.reason_code)):
        parser.error('acknowledgement requires --ack-alert, --actor and --reason-code')
    store = ShadowStore(ROOT / "data/shadow/ndx_range")
    with FileLock(store.root / "monitor.lock"):
        if args.ack_alert:
            store.acknowledge_alert(args.ack_alert, args.actor, args.reason_code, datetime.now(timezone.utc))
        try:
            status = json.loads((ROOT / "reports/phase3h_shadow_status.json").read_text())
        except (FileNotFoundError, ValueError):
            status = None
        try:
            verification = json.loads((ROOT / "reports/phase3l_forward_audit.json").read_text())
        except (FileNotFoundError, ValueError):
            verification = None
        report = monitor_operations(store, status, datetime.now(timezone.utc), outcome_verification=verification)
        destination = ROOT / "reports/phase3j_operations.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
    print(json.dumps({"status": report["status"], "open_alerts": len(report["open_alerts"]),
                      "issued": report["issued"], "matured": report["matured"]}))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
