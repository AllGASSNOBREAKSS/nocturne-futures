"""Verified provider registry plus bounded free-data snapshots."""
import json
from pathlib import Path

from nocturne.adapters.bls import SERIES as BLS_SERIES, fetch_series, save
from nocturne.adapters.registry import registry

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = registry()
    report["bls_snapshot"] = None
    try:
        result = fetch_series(list(BLS_SERIES), 2024, 2025)
        report["bls_snapshot"] = {"status": "VERIFIED", **save(result, ROOT / "data/history/bls"),
                                  "non_null": sum(1 for row in result["rows"] if row["value"] is not None),
                                  "point_in_time_eligible": False,
                                  "note": "monthly period only; no release timestamp or consensus"}
    except Exception as exc:  # adapter boundary
        report["bls_snapshot"] = {"status": "DATA_BLOCKED", "error_type": type(exc).__name__}
    fred = sorted((ROOT / "data/history/fred").glob("*.json"))
    report["fred_snapshot"] = {"manifests": len(fred), "status": "VERIFIED" if fred else "MISSING"}
    report["secrets"] = {
        "policy": "environment variables only; values are never logged or committed",
        "required_for_licensed_futures": ["DATABENTO_API_KEY"],
        "optional": ["FRED_API_KEY", "BLS_API_KEY", "NASDAQ_DATA_LINK_API_KEY"],
    }
    (ROOT / "reports/phase3g_providers.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"statuses": {p["name"]: p["status"] for p in report["providers"]},
                      "bls": report["bls_snapshot"]["status"]}, indent=1))


if __name__ == "__main__":
    main()
