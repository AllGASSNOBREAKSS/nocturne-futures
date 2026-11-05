"""Non-consumption access report and bounded jobs; never automatically download."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import requests

from nocturne.adapters.databento_access import DatabentoAccess
from nocturne.adapters.snapshots import canonical, digest, immutable_write
from nocturne.research.orchestrator import JobStore, run_lane

ROOT = Path(__file__).resolve().parents[1]
URLS = ("https://databento.com/docs/knowledge-base/datasets/glbx-mdp3", "https://databento.com/pricing", "https://databento.com/docs/api-historical")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-docs", action="store_true")
    parser.add_argument("--research-check", action="store_true")
    args = parser.parse_args()
    archive = ROOT / "data/licensed/databento_metadata"
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "DATA_BLOCKED",
              "trading_decision": "NO_TRADE", "consumption_attempted": False, "credit_eligibility": "UNVERIFIED_ACCOUNT_SPECIFIC",
              "provider_cost_usd": None, "public_sources": [], "pilots": [], "research_jobs": []}
    if args.public_docs:
        for url in URLS:
            try:
                response = requests.get(url, timeout=30)
                entry = {"url": url, "http_status": response.status_code, "received_at": datetime.now(timezone.utc).isoformat()}
                if response.status_code == 200:
                    entry["body_sha256"] = digest(response.content)
                    entry["bytes"] = len(response.content)
                    immutable_write(archive / "public_docs" / entry["body_sha256"], response.content)
                    entry["limitation"] = "page retrieval does not prove rendered pricing, account eligibility or entitlement"
                report["public_sources"].append(entry)
            except requests.RequestException as exc:
                report["public_sources"].append({"url": url, "status": "UNAVAILABLE", "reason": type(exc).__name__})
    client = DatabentoAccess()
    for instrument, contract in (("NQ", "NQZ6"), ("ES", "ESZ6")):
        quote = client.preflight(archive, contract=contract, instrument=instrument,
                                  start="2026-11-01T23:00:00Z", end="2026-11-02T22:00:00Z")
        report["pilots"].append(quote)
    if all(q["status"] == "QUOTED_AWAITING_OPERATOR_APPROVAL" for q in report["pilots"]):
        from decimal import Decimal
        report["status"] = "AWAITING_EXPLICIT_CONSUMPTION_AUTHORIZATION"
        report["provider_cost_usd"] = str(sum(Decimal(q["cost_usd"]) for q in report["pilots"]))
    if args.research_check:
        store = JobStore(ROOT / "data/research/orchestrator")
        inventory = [{"name": p.name, "sha256": digest(p.read_bytes())} for p in sorted((ROOT / "data/licensed/databento").glob("*.json"))]
        code = b"".join((ROOT / name).read_bytes() for name in ("src/nocturne/research/futures_pilot.py", "src/nocturne/backtest/engine.py", "src/nocturne/research/contract_replay.py", "src/nocturne/research/target_dataset.py"))
        version = digest(canonical({"receipts": inventory, "code": digest(code)}))
        ids = [store.submit("HISTORICAL_BACKTEST", "research", f"raw_futures_v3|{instrument}|{version}",
                           {"scope": "raw_futures", "instrument": instrument, "contract": contract}, max_attempts=1)
               for instrument, contract in (("NQ", "NQZ6"), ("ES", "ESZ6"))]
        report["runner"] = run_lane(store, ROOT, "research", max_jobs=2, budget_seconds=600, only_ids=set(ids))
        report["research_jobs"] = [j for j in store.jobs() if j["id"] in ids]
    identifier = digest(canonical(report))
    immutable_write(archive / "reports" / f"{identifier}.json", canonical(report))
    (ROOT / "reports/phase3n_futures_access.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "provider_cost_usd": report["provider_cost_usd"],
                      "consumption_attempted": False, "research_jobs": [j["state"] for j in report["research_jobs"]]}))
    return 1 if report["status"] == "DATA_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
