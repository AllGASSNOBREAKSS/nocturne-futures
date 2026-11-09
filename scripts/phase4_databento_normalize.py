"""Normalize acquired Databento 1-minute chunks into per-root research tables.

Reads only COMPLETED ledger chunks (checksummed), validates each, attaches the
actual contract (raw_symbol) per bar from the definition records, flags roll
minutes (contract change), and writes ignored, licensed outputs:
  data/licensed/databento/normalized/{NQ,ES}_1m.csv.gz + manifest.json
Writes reports/phase4_databento_quality.json (aggregate statistics only).
"""
import gzip
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nocturne.adapters.databento_bulk import read_chunk, validate_ohlcv

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/licensed/databento"


def aggregate(g, rule):
    """Aggregate within one contract only; a bucket containing a roll keeps the
    contract with more volume. Daily bars use the Globex session (18:00 ET)."""
    frame = g[["ts_event", "open", "high", "low", "close", "volume", "instrument_id", "contract"]].copy()
    if rule is None:
        et = frame.ts_event.dt.tz_convert("America/New_York")
        frame["bucket"] = pd.to_datetime((et + pd.Timedelta(hours=6)).dt.date).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    else:
        frame["bucket"] = frame.ts_event.dt.floor(rule)
    agg = frame.groupby(["bucket", "instrument_id"], sort=True).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                                                     close=("close", "last"), volume=("volume", "sum"),
                                                                     contract=("contract", "first"), minutes=("open", "size")).reset_index()
    agg = agg.sort_values(["bucket", "volume"]).drop_duplicates("bucket", keep="last").reset_index(drop=True)
    agg["roll"] = agg.instrument_id.ne(agg.instrument_id.shift()).astype(int)
    agg.loc[0, "roll"] = 0
    agg.insert(0, "timestamp", agg.pop("bucket").dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return agg


def main():
    ledger = [json.loads(x) for x in (STORE / "spend_ledger.jsonl").read_text().splitlines() if x.strip()]
    done = {e["chunk_id"]: e for e in ledger if e["event"] == "COMPLETED"}
    for e in done.values():
        if hashlib.sha256((STORE / e["raw_file"]).read_bytes()).hexdigest() != e["raw_sha256"]:
            raise SystemExit(f"checksum mismatch {e['chunk_id']}")
    defs = read_chunk(STORE / done["definition_2010_2026"]["raw_file"]).sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    # Raw symbols repeat each decade (NQZ6 = 2016 and 2026); label with the expiry year.
    expiry = pd.to_datetime(defs.expiration, utc=True, errors="coerce").dt.year.astype("Int64").astype(str)
    contract = (defs.raw_symbol + "-" + expiry).set_axis(defs.instrument_id)
    frames, checks = [], {}
    for chunk_id in sorted(k for k in done if k.startswith("ohlcv1m_")):
        clean, check = validate_ohlcv(read_chunk(STORE / done[chunk_id]["raw_file"]), defs)
        checks[chunk_id] = check
        frames.append(clean)
    data = pd.concat(frames, ignore_index=True)
    before = len(data)
    data = data.drop_duplicates(["symbol", "ts_event"]).sort_values(["symbol", "ts_event"]).reset_index(drop=True)
    data["contract"] = data.instrument_id.map(contract)
    out_dir = STORE / "normalized"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest, quality = {}, {"generated_at": datetime.now(timezone.utc).isoformat(), "chunks": checks,
                             "cross_chunk_duplicates_removed": int(before - len(data)), "roots": {}}
    for root, g in data.groupby("root"):
        g = g.reset_index(drop=True)
        roll = g.instrument_id.ne(g.instrument_id.shift()) & g.index.to_series().gt(0)
        rolls = g[roll]
        gaps = g.ts_event.diff().dt.total_seconds().div(60)
        table = pd.DataFrame({"timestamp": g.ts_event.dt.strftime("%Y-%m-%dT%H:%M:%SZ"), "open": g.open, "high": g.high, "low": g.low,
                              "close": g.close, "volume": g.volume.astype("int64"), "instrument_id": g.instrument_id,
                              "contract": g.contract, "roll_minute": roll.astype(int)})
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
            gz.write(table.to_csv(index=False, lineterminator="\n").encode())
        path = out_dir / f"{root}_1m.csv.gz"
        path.write_bytes(buf.getvalue())
        for interval, rule in (("5m", "5min"), ("1h", "1h"), ("1d", None)):
            agg = aggregate(g, rule)
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
                gz.write(agg.to_csv(index=False, lineterminator="\n").encode())
            (out_dir / f"{root}_{interval}.csv.gz").write_bytes(buf.getvalue())
            manifest[f"{root}_{interval}"] = {"file": f"{root}_{interval}.csv.gz", "rows": int(len(agg)),
                                              "sha256": hashlib.sha256(buf.getvalue()).hexdigest()}
        manifest[root] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": int(len(table)),
                          "first": table.timestamp.iloc[0], "last": table.timestamp.iloc[-1]}
        quality["roots"][root] = {"rows": int(len(table)), "first": table.timestamp.iloc[0], "last": table.timestamp.iloc[-1],
                                  "contracts": int(g.instrument_id.nunique()), "rolls": int(len(rolls)),
                                  "roll_dates_sample": rolls.ts_event.dt.date.astype(str).tail(6).tolist(),
                                  "contracts_sample": g.contract.dropna().unique()[-6:].tolist(),
                                  "unknown_contract_rows": int(g.contract.isna().sum()),
                                  "gaps_over_60min": int((gaps > 60).sum()), "gaps_over_3days": int((gaps > 4320).sum()),
                                  "volume_total": int(g.volume.sum()),
                                  "largest_abs_1m_return_pct": float((g.close.pct_change().where(~roll).abs().max()) * 100)}
    (out_dir / "manifest.json").write_text(json.dumps({"generated_at": quality["generated_at"], "source": "Databento GLBX.MDP3 ohlcv-1m continuous v.0",
                                                       "license": "licensed; private research only; not committed", **manifest}, indent=2))
    (ROOT / "reports/phase4_databento_quality.json").write_text(json.dumps(quality, indent=2, default=str) + "\n")
    print(json.dumps(quality["roots"], indent=1, default=str))


if __name__ == "__main__":
    main()
