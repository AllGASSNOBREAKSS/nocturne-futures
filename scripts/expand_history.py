"""Fetch public macro context or import a licensed futures CSV export."""
import argparse
import json
from pathlib import Path

from nocturne.adapters.fred import SERIES, fetch_context
from nocturne.adapters.history import ingest_export
from nocturne.adapters.yahoo import fetch_chart, events_from_chart, bars_frame

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("fred-context")
    sub.add_parser("yahoo-hourly")
    csv = sub.add_parser("import-csv")
    csv.add_argument("path", type=Path)
    for arg in ("provider", "instrument", "interval", "price-basis", "license-scope"):
        csv.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    if args.mode == "yahoo-hourly":
        root = ROOT / "data/history/yahoo_hourly"
        root.mkdir(parents=True, exist_ok=True)
        results = []
        for instrument in ("NQ", "ES"):
            try:
                payload = fetch_chart(instrument + "=F", range_="2y", interval="60m", retries=1)
                import hashlib
                raw = json.dumps(payload, sort_keys=True).encode()
                digest = hashlib.sha256(raw).hexdigest()
                (root / f"{instrument}_{digest}.json").write_bytes(raw)
                frame = bars_frame(events_from_chart(payload, instrument + "=F", "60m"))
                export = root / f"{instrument}_60m.csv"
                frame.to_csv(export, index=False)
                record = ingest_export(export, root / instrument, provider="yahoo_public_unofficial",
                                       instrument=instrument, interval="1h", price_basis="unknown",
                                       license_scope="research_context_not_exchange_feed")
                results.append({"status": "FETCHED", "raw_json_sha256": digest, **record,
                                "five_minute_session_eligible": False,
                                "limitation": "hourly bars cannot resolve 09:30 boundaries or 5-minute barriers"})
            except Exception as exc:
                results.append({"instrument": instrument, "status": "DATA_BLOCKED", "error_type": type(exc).__name__})
        (ROOT / "reports/phase3d_hourly_inventory.json").write_text(json.dumps(results, indent=2, default=bool) + "\n")
        print(json.dumps(results, indent=2, default=bool))
        return
    if args.mode == "import-csv":
        print(json.dumps(ingest_export(args.path, ROOT / "data/history/futures",
                         provider=args.provider, instrument=args.instrument, interval=args.interval,
                         price_basis=args.price_basis, license_scope=args.license_scope), indent=2))
        return
    results = []
    for series in SERIES:
        try:
            results.append({"status": "FETCHED", **fetch_context(series, ROOT / "data/history/fred")})
        except Exception as exc:
            # Never log response bodies or credential-bearing URLs at this boundary.
            results.append({"series": series, "status": "DATA_BLOCKED", "error_type": type(exc).__name__})
    (ROOT / "reports/phase3d_macro_inventory.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
