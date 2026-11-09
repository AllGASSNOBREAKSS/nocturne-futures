"""Phase 3V Databento metadata/cost preflight. No time-series consumption.

Uses only free metadata/symbology endpoints through the existing
DatabentoAccess allow-list. Every response is archived by SHA-256 under the
ignored licensed directory; the report never contains credentials or URLs.
"""
import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from nocturne.adapters.databento_access import DatabentoAccess

ROOT = Path(__file__).resolve().parents[1]
DATASET = "GLBX.MDP3"
# Front-month continuous by volume returns the actual traded contract per bar;
# instrument_id and the symbology map identify every roll.
FRONT = "NQ.v.0,ES.v.0"
TRANCHES = {
    "pilot_ohlcv_1m_2w": dict(symbols=FRONT, stype_in="continuous", schema="ohlcv-1m", start="2026-10-26", end="2026-11-07"),
    "pilot_definition_2w": dict(symbols=FRONT, stype_in="continuous", schema="definition", start="2026-10-26", end="2026-11-07"),
    "ohlcv_1m_2021_2026": dict(symbols=FRONT, stype_in="continuous", schema="ohlcv-1m", start="2021-01-01", end="2026-11-07"),
    "ohlcv_1m_2010_2020": dict(symbols=FRONT, stype_in="continuous", schema="ohlcv-1m", start="2010-06-06", end="2021-01-01"),
    "ohlcv_1m_all_expiries_parent_1y": dict(symbols="NQ.FUT,ES.FUT", stype_in="parent", schema="ohlcv-1m", start="2025-11-01", end="2026-11-07"),
    "definition_2010_2026": dict(symbols=FRONT, stype_in="continuous", schema="definition", start="2010-06-06", end="2026-11-07"),
    "trades_1m_month": dict(symbols=FRONT, stype_in="continuous", schema="trades", start="2026-10-01", end="2026-11-01"),
    "tbbo_1_month": dict(symbols=FRONT, stype_in="continuous", schema="tbbo", start="2026-10-01", end="2026-11-01"),
    "trades_2021_2026": dict(symbols=FRONT, stype_in="continuous", schema="trades", start="2021-01-01", end="2026-11-07"),
    "mbp1_1_week": dict(symbols=FRONT, stype_in="continuous", schema="mbp-1", start="2026-10-26", end="2026-11-02"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/licensed/databento/metadata")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/phase3v_preflight.json")
    args = parser.parse_args()
    access = DatabentoAccess()
    receipts = []

    def call(method, params):
        value, receipt = access._call(method, params, args.archive)
        receipts.append(receipt)
        return value

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "dataset": DATASET,
              "time_series_requested": False, "credential": "loaded from private file into process env; never logged"}
    report["authenticated"] = DATASET in call("metadata.list_datasets", {})
    report["schemas"] = call("metadata.list_schemas", {"dataset": DATASET})
    span = call("metadata.get_dataset_range", {"dataset": DATASET})
    report["range"] = {"start": span["start"], "end": span["end"],
                       "by_schema": {k: v for k, v in span.get("schema", span.get("range_by_schema", {})).items()
                                     if k in ("ohlcv-1m", "trades", "tbbo", "mbp-1", "mbo", "definition")}}
    try:
        report["unit_prices"] = call("metadata.list_unit_prices", {"dataset": DATASET})
    except ValueError as exc:
        report["unit_prices"] = f"UNAVAILABLE: {exc}"
    resolved = call("symbology.resolve", {"dataset": DATASET, "symbols": FRONT, "stype_in": "continuous",
                                          "stype_out": "instrument_id", "start_date": "2010-06-06", "end_date": "2026-11-07"})
    report["symbology"] = {"status": resolved.get("status"), "partial": resolved.get("partial"),
                           "not_found": resolved.get("not_found"),
                           "intervals": {s: len(v) for s, v in resolved.get("result", {}).items()},
                           "first": {s: v[0] for s, v in resolved.get("result", {}).items() if v},
                           "last": {s: v[-1] for s, v in resolved.get("result", {}).items() if v}}
    quotes, total = {}, Decimal(0)
    for name, spec in TRANCHES.items():
        params = {"dataset": DATASET, **spec}
        try:
            quote = {"request": params,
                     "cost_usd": str(Decimal(str(call("metadata.get_cost", params)))),
                     "billable_bytes": int(call("metadata.get_billable_size", params)),
                     "record_count": int(call("metadata.get_record_count", params))}
        except ValueError as exc:
            quote = {"request": params, "error": str(exc)}
        quotes[name] = quote
    report["quotes"] = quotes
    report["account_credit_balance"] = ("NOT_EXPOSED_BY_HISTORICAL_API: confirm remaining credits in the "
                                        "Databento portal (Billing) before approving")
    report["metadata_receipts"] = receipts
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, q in quotes.items():
        print(f"{name:34} ${q.get('cost_usd', q.get('error')):>12}  {q.get('billable_bytes', 0)/2**20:10.1f} MiB  {q.get('record_count', 0):>12,} rows")
    print(json.dumps({k: report[k] for k in ("authenticated", "symbology")}, default=str)[:900])


if __name__ == "__main__":
    main()
