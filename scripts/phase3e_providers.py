"""Inventory credentials by presence only, or explicitly fetch licensed data."""
import argparse
import json
import os
from pathlib import Path

from nocturne.adapters.databento import DatabentoBars
from nocturne.adapters.alfred import fetch_vintage

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("inventory")
    bars = sub.add_parser("databento")
    for name in ("contract", "instrument", "start", "end", "license-scope"):
        bars.add_argument("--" + name, required=True)
    bars.add_argument("--quote", type=Path, required=True, help="saved authenticated metadata quote")
    bars.add_argument("--approval", type=Path, required=True, help="explicit operator approval bound to that quote")
    vintage = sub.add_parser("alfred")
    vintage.add_argument("--series", required=True)
    vintage.add_argument("--vintage", required=True)
    args = parser.parse_args()
    private = ROOT / "data/licensed"
    if args.mode == "databento":
        result = DatabentoBars().download(private / "databento", contract=args.contract,
                     instrument=args.instrument, start=args.start, end=args.end, license_scope=args.license_scope,
                     quote=json.loads(args.quote.read_text()), approval=json.loads(args.approval.read_text()))
        print(json.dumps({"chunks": len(result), "rows": sum(r["rows"] for r in result)}))
    elif args.mode == "alfred":
        result = fetch_vintage(args.series, args.vintage)
        private.mkdir(parents=True, exist_ok=True)
        (private / "alfred_snapshot.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"observations": len(result)}))
    else:
        result = {name: {"credential_present": bool(os.environ.get(key)),
                        "real_data_status": "ENTITLEMENT_UNVERIFIED" if os.environ.get(key) else "DATA_BLOCKED"}
                  for name, key in (("databento", "DATABENTO_API_KEY"), ("alfred", "FRED_API_KEY"))}
        result["unsupported_real_data"] = ["licensed ticks/depth/MBO", "VX futures", "historical consensus", "authorized news"]
        (ROOT / "reports/phase3e_providers.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
