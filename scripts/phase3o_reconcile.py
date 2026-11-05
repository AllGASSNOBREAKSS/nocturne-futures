"""Deliberate investigation; --apply appends proof only, never a forecast/outcome."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from nocturne.adapters.snapshots import SnapshotStore, canonical, digest, immutable_write
from nocturne.shadow import ShadowStore
from nocturne.shadow.reconciliation import investigate_revision, verify_reconciliation
from phase3k_reconcile import import_existing, reference_check

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--reference-check", action="store_true")
    args = parser.parse_args()
    store = ShadowStore(ROOT / "data/shadow/ndx_range")
    before = {p: p.read_bytes() if p.exists() else b"" for p in (store.forecast_path, store.outcome_path)}
    forecast = next(f for f in store.forecasts() if f["forecast_id"] == args.forecast_id)
    archive = SnapshotStore(ROOT / "data/shadow/market/snapshots")
    current_id = import_existing(ROOT / "data/shadow/market", "^NDX", archive)
    report = investigate_revision(forecast, archive, current_id, datetime.now(timezone.utc))
    previous_path = ROOT / "reports/phase3o_reconciliation.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    same = previous.get("record", {}).get("forecast_sha256") == report["record"]["forecast_sha256"] and previous.get("record", {}).get("revised_reference_bar_sha256") == report["record"]["revised_reference_bar_sha256"]
    report["source_checks"] = reference_check(archive.root, forecast["data_date"]) if args.reference_check else previous.get("source_checks", []) if same else []
    report["decision"] = "VERIFIED_AS_ISSUED_PROVIDER_REVISION"
    report["applied"] = False
    if args.apply:
        prior = next((r for r in store.reconciliations() if r["forecast_id"] == forecast["forecast_id"]
                      and r.get("revised_reference_bar_sha256") == report["record"]["revised_reference_bar_sha256"]), None)
        if prior:
            current = archive.frame(current_id)
            bar = current[current.date == forecast["data_date"]].iloc[0]
            verify_reconciliation(forecast, prior, archive, float(bar.close), current_bar=bar)
        report["reconciliation"] = prior or store.append_reconciliation(report["record"])
        report["applied"] = True
    for path, content in before.items():
        if content != (path.read_bytes() if path.exists() else b""):
            raise ValueError("journal changed during deliberate investigation")
    report["journal_bytes_unchanged"] = True
    report["outcome_status"] = "not evaluated by this command; original maturity gates remain required"
    immutable_write(archive.root / "investigations" / f"{digest(canonical(report))}.json", canonical(report))
    (ROOT / "reports/phase3o_reconciliation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"decision": report["decision"], "applied": report["applied"], "changes": report["changes"], "journal_bytes_unchanged": True}))


if __name__ == "__main__":
    main()
