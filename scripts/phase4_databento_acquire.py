"""Phase 4: credit-bounded NQ/ES 1-minute history from Databento (2010 -> latest).

Order: contract definitions -> 2-week pilot -> pilot validation gate -> yearly
chunks (oldest first). Run cap and cumulative credit ceiling are enforced per
chunk. Licensed data stays under ignored data/licensed/databento/. Writes
reports/phase4_databento_acquisition.json (no credentials).
"""
import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nocturne.adapters.databento_bulk import Acquirer, CreditGuard, DATASET, read_chunk, validate_ohlcv

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/licensed/databento"
SYMBOLS = "NQ.v.0,ES.v.0"
PILOT = ("2026-10-25", "2026-11-08")


def params(schema, start, end):
    return {"dataset": DATASET, "symbols": SYMBOLS, "stype_in": "continuous", "schema": schema, "start": start, "end": end}


def definitions_table(record):
    frame = read_chunk(STORE / record["raw_file"])
    keep = [c for c in ("ts_recv", "instrument_id", "raw_symbol", "symbol", "instrument_class", "min_price_increment",
                        "display_factor", "unit_of_measure_qty", "expiration", "activation", "currency", "exchange", "asset") if c in frame]
    frame = frame[keep].sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    return frame


def yahoo_crosscheck(clean):
    """Independent free-source check: Databento 1m aggregated to 5m vs Yahoo 5m closes."""
    from nocturne.studio import market
    out = {}
    for root in ("NQ", "ES"):
        db = clean[clean.root == root].set_index("ts_event")
        five = db.close.resample("5min", label="left", closed="left").last().dropna()
        yahoo, _ = market.bars(root, "5m", limit=100000)
        y = yahoo.set_index("timestamp").close
        both = five.index.intersection(y.index)
        diff = (five.loc[both] - y.loc[both]).abs()
        out[root] = {"matched_5m_bars": int(len(both)), "median_abs_close_diff": float(diff.median()) if len(both) else None,
                     "share_within_1_tick": float((diff <= 0.25).mean()) if len(both) else None}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-cap", type=float, default=50.0)
    parser.add_argument("--ceiling", type=float, default=125.0)
    parser.add_argument("--end", default="2026-11-08")
    args = parser.parse_args()
    acq = Acquirer(STORE, args.run_cap, args.ceiling)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "run_cap_usd": args.run_cap, "credit_ceiling_usd": args.ceiling,
              "operator_authorization": "Operator stated $125 promotional credits and authorized credit-only historical acquisition (2026-11-09).",
              "live_data": False, "chunks": [], "status": "RUNNING"}
    out = ROOT / "reports/phase4_databento_acquisition.json"
    try:
        definition = acq.chunk("definition_2010_2026", params("definition", "2010-06-06", args.end))
        report["chunks"].append(definition)
        defs = definitions_table(definition)
        report["definitions"] = {"instruments": int(len(defs)), "raw_symbols_sample": defs.raw_symbol.tail(8).tolist() if "raw_symbol" in defs else None,
                                 "min_price_increment": sorted(defs.min_price_increment.unique().tolist()) if "min_price_increment" in defs else None,
                                 "multiplier": sorted(defs.unit_of_measure_qty.dropna().unique().tolist()) if "unit_of_measure_qty" in defs else None}
        pilot = acq.chunk("ohlcv1m_pilot", params("ohlcv-1m", *PILOT))
        report["chunks"].append(pilot)
        clean, check = validate_ohlcv(read_chunk(STORE / pilot["raw_file"]), defs)
        check["yahoo_crosscheck"] = yahoo_crosscheck(clean)
        report["pilot_validation"] = check
        gate = (check["rows"] > 0 and check["minute_aligned"] and check["off_tick_prices"] == 0 and check.get("unknown_instrument_ids", 0) == 0
                and check["ohlc_inconsistent"] == 0 and all((v["median_abs_close_diff"] or 0) <= 1.0 for v in check["yahoo_crosscheck"].values()))
        report["pilot_gate"] = "PASSED" if gate else "FAILED"
        if not gate:
            raise CreditGuard("pilot validation failed; no further chunks requested")
        years = [(f"{y}-01-01" if y > 2010 else "2010-06-06", f"{y + 1}-01-01" if y < 2026 else PILOT[0]) for y in range(2010, 2027)]
        for start, end in years:
            report["chunks"].append(acq.chunk(f"ohlcv1m_{start[:4]}", params("ohlcv-1m", start, end)))
            out.write_text(json.dumps(report, indent=2, default=str) + "\n")
        report["status"] = "COMPLETED"
    except CreditGuard as exc:
        report["status"] = "STOPPED"
        report["stop_reason"] = str(exc)
    report["spend"] = {"run_quoted_usd": str(acq.run_spent), "cumulative_reserved_quoted_usd": str(acq.committed()),
                       "remaining_of_ceiling_usd": str(acq.ceiling - acq.committed()),
                       "note": "Quoted costs from Databento metadata.get_cost; confirm actual usage in the portal."}
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report.get(k) for k in ("status", "stop_reason", "pilot_gate", "spend")}, default=str))
    print(json.dumps(report.get("pilot_validation"), default=str)[:1200])


if __name__ == "__main__":
    main()
