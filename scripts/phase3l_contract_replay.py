"""Run existing contract replay/target labels only on verified local receipts."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from nocturne.instruments import get_instrument
from nocturne.research.contract_replay import load_contract_receipts, asof_contract_context, target_distance_study
from nocturne.research.contract_targets import ContractSetup

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", choices=("NQ", "ES"), required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--session", default="NEW_YORK", choices=("ASIA", "LONDON", "NEW_YORK", "RTH", "ETH"))
    parser.add_argument("--setups", type=Path)
    args = parser.parse_args()
    spec = get_instrument(args.instrument)
    history = load_contract_receipts(ROOT / "data/licensed/databento", spec, args.contract)
    context = asof_contract_context(history, spec, args.contract, datetime.fromisoformat(args.day).date(), args.session, args.asof)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": history["status"], "context": context,
              "receipts": history["receipts"], "target_rows": 0, "trading_decision": "NO_TRADE"}
    if args.setups and history["status"] != "DATA_BLOCKED":
        setups = [ContractSetup(**row) for row in json.loads(args.setups.read_text())]
        dataset = target_distance_study(history, spec, setups)
        report["target_rows"] = len(dataset)
        destination = ROOT / "data/licensed/research"
        destination.mkdir(parents=True, exist_ok=True)
        dataset.to_csv(destination / f"{args.contract}_target_grid.csv", index=False)
    (ROOT / "reports/phase3l_contract_replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "target_rows": report["target_rows"]}))
    return 1 if history["status"] == "DATA_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
