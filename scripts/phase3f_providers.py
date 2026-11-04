"""Provider readiness: requirements, local coverage and volume estimates.

Never prints credential values. Prices are not estimated here: Databento bills by
usage and entitlement, so callers must query the provider's cost endpoint.
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = {"NQ": "NQ", "ES": "ES"}


def local_coverage():
    coverage = {}
    for name, path, frequency in (
        ("NQ_5m", "data/market/intraday/NQ_5m.csv", "5m"),
        ("ES_5m", "data/market/intraday/ES_5m.csv", "5m"),
        ("NQ_1h", "data/history/yahoo_hourly/NQ_60m.csv", "1h"),
        ("ES_1h", "data/history/yahoo_hourly/ES_60m.csv", "1h"),
        ("NQ_daily", "data/market/daily/NQ.csv", "1d"),
        ("ES_daily", "data/market/daily/ES.csv", "1d"),
    ):
        full = ROOT / path
        if not full.exists():
            coverage[name] = {"status": "MISSING"}
            continue
        frame = pd.read_csv(full)
        stamp = "timestamp" if "timestamp" in frame else "date"
        dates = pd.to_datetime(frame[stamp], utc=True, errors="coerce")
        coverage[name] = {"rows": len(frame), "first": str(dates.min()), "last": str(dates.max()),
                          "frequency": frequency, "contract_ids": "contract_id" in frame}
    return coverage


def volume_estimate(years=5, hours=23, weekdays=252):
    return {
        "assumption": f"{hours}h/day x {weekdays} days/year x {years} years",
        "one_minute_rows_per_instrument": hours * 60 * weekdays * years,
        "five_minute_rows_per_instrument": hours * 12 * weekdays * years,
        "note": "row counts only; obtain billable size and cost from the provider metadata endpoints",
    }


def main():
    report = {
        "credentials": {
            "DATABENTO_API_KEY": {"present": bool(os.environ.get("DATABENTO_API_KEY")),
                                  "purpose": "licensed CME GLBX raw-contract OHLCV/trades/depth",
                                  "status": "UNVERIFIED" if os.environ.get("DATABENTO_API_KEY") else "DATA_BLOCKED"},
            "FRED_API_KEY": {"present": bool(os.environ.get("FRED_API_KEY")),
                             "purpose": "ALFRED real-time vintage observations",
                             "status": "UNVERIFIED" if os.environ.get("FRED_API_KEY") else "DATA_BLOCKED"},
            "POLYGON_API_KEY": {"present": bool(os.environ.get("POLYGON_API_KEY")),
                                "purpose": "alternative licensed aggregates (adapter not implemented)",
                                "status": "NOT_IMPLEMENTED"},
        },
        "databento": {
            "endpoint": "https://hist.databento.com/v0/timeseries.get_range",
            "dataset": "GLBX.MDP3",
            "schema": "ohlcv-1m",
            "symbol_type": "raw_symbol (one explicit contract per request)",
            "supported_instruments": INSTRUMENTS,
            "requires": ["entitlement for GLBX.MDP3", "raw contract symbols", "license acceptance"],
            "implemented": True, "verified_with_real_data": False,
            "blocking": "no credential present; entitlement and licensing unverified",
        },
        "alfred": {
            "endpoint": "https://api.stlouisfed.org/fred/series/observations",
            "requires": ["free FRED API key"],
            "limitations": ["date precision only", "no intraday release clock", "no consensus"],
            "implemented": True, "verified_with_real_data": False,
            "blocking": "no credential present",
        },
        "not_implemented_sources": ["CME DataMine", "Nasdaq Data Link", "licensed news/consensus feeds"],
        "local_coverage": local_coverage(),
        "volume_estimate": volume_estimate(),
        "data_integrity_requirements": [
            "one contract per request; never stitch rolls into raw history",
            "explicit UTC availability at bar end; exchange calendar for completeness",
            "reject duplicate timestamps and conflicting revisions",
            "bid/ask, depth and MBO only if licensed and sequence-validated",
        ],
    }
    (ROOT / "reports/phase3f_providers.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"credentials": {k: v["status"] for k, v in report["credentials"].items()},
                      "local": list(report["local_coverage"])}))


if __name__ == "__main__":
    main()
