"""Ingest long daily history for free, provenance-tracked research context."""
import json
import time
from pathlib import Path

from nocturne.adapters.yahoo_history import DEFAULT_SYMBOLS, fetch_daily_history

ROOT = Path(__file__).resolve().parents[1]


def main():
    root = ROOT / "data/history/yahoo_daily"
    results = []
    for symbol in DEFAULT_SYMBOLS:
        try:
            manifest = fetch_daily_history(symbol, root)
            results.append({"status": "FETCHED", **manifest})
            print(symbol, manifest["rows"], manifest["first"], manifest["last"])
        except Exception as exc:  # adapter boundary
            results.append({"symbol": symbol, "status": "DATA_BLOCKED",
                            "error_type": type(exc).__name__})
            print(symbol, "BLOCKED", type(exc).__name__)
        time.sleep(2.0)
    report = {"provider": "yahoo_public_unofficial", "results": results,
              "notes": ["index levels are context, not tradable instruments",
                        "continuous futures proxies lack verified roll mapping",
                        "no adjusted-price reconstruction performed"]}
    (ROOT / "reports/phase3g_daily_ingest.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
