"""Credit-bounded Databento historical acquisition (no live data, no subscriptions).

Every chunk is re-quoted with the free metadata API immediately before download,
checked against a per-run cap and a cumulative ceiling recorded in an append-only
spend ledger, and durably RESERVED before the network request. A reservation
without a completion stops the run for operator review: chunks are never
auto-retried, so an uncertain attempt cannot be billed twice. Completed chunks
are content-addressed and skipped on re-runs. Raw provider bytes are kept
separately from normalized research tables; nothing here is committed to git.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import requests

BASE = "https://hist.databento.com/v0/"
DATASET = "GLBX.MDP3"
TICK = {"NQ": 0.25, "ES": 0.25}


def _now():
    return datetime.now(timezone.utc).isoformat()


class CreditGuard(Exception):
    """Spending rule would be violated; nothing was requested."""


class Acquirer:
    def __init__(self, root, run_cap_usd, ceiling_usd, key=None, session=None):
        self.root = Path(root)
        self.key = key or os.environ.get("DATABENTO_API_KEY")
        if not self.key:
            raise CreditGuard("DATABENTO_API_KEY missing")
        self.session = session or requests.Session()
        self.run_cap, self.ceiling = Decimal(str(run_cap_usd)), Decimal(str(ceiling_usd))
        self.ledger = self.root / "spend_ledger.jsonl"
        self.run_spent = Decimal(0)

    def entries(self):
        return [json.loads(x) for x in self.ledger.read_text().splitlines() if x.strip()] if self.ledger.exists() else []

    def committed(self):
        """Quoted cost of every reserved chunk (completed or uncertain) counts as spent."""
        return sum((Decimal(e["quoted_cost_usd"]) for e in self.entries() if e["event"] == "RESERVED"), Decimal(0))

    def _log(self, record):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _meta(self, method, params):
        r = self.session.get(BASE + method, params=params, auth=(self.key, ""), timeout=(10, 60))
        if r.status_code != 200:
            raise CreditGuard(f"METADATA_HTTP_{r.status_code}")
        return r.text

    def quote(self, params):
        return {"cost_usd": str(Decimal(self._meta("metadata.get_cost", params))),
                "billable_bytes": int(self._meta("metadata.get_billable_size", params)),
                "record_count": int(self._meta("metadata.get_record_count", params))}

    def chunk(self, chunk_id, params):
        """Acquire one chunk; return its completion record (or the stored one)."""
        done = {e["chunk_id"]: e for e in self.entries() if e["event"] == "COMPLETED"}
        if chunk_id in done:
            record = done[chunk_id]
            if hashlib.sha256((self.root / record["raw_file"]).read_bytes()).hexdigest() != record["raw_sha256"]:
                raise CreditGuard(f"stored chunk {chunk_id} checksum mismatch; operator review required")
            return {**record, "reused": True}
        if any(e["chunk_id"] == chunk_id and e["event"] == "RESERVED" for e in self.entries()):
            raise CreditGuard(f"chunk {chunk_id} has an uncompleted reservation; never auto-retried (operator review)")
        q = self.quote(params)
        cost = Decimal(q["cost_usd"])
        if self.run_spent + cost > self.run_cap:
            raise CreditGuard(f"run cap ${self.run_cap} would be exceeded by {chunk_id} (${cost})")
        if self.committed() + cost > self.ceiling:
            raise CreditGuard(f"credit ceiling ${self.ceiling} would be exceeded by {chunk_id} (${cost})")
        self._log({"event": "RESERVED", "chunk_id": chunk_id, "at": _now(), "request": params,
                   "quoted_cost_usd": q["cost_usd"], "billable_bytes": q["billable_bytes"], "record_count": q["record_count"]})
        self.run_spent += cost
        request = {**params, "encoding": "csv", "compression": "zstd", "pretty_px": "true", "pretty_ts": "true", "map_symbols": "true"}
        raw_dir = self.root / "raw" / params["schema"]
        raw_dir.mkdir(parents=True, exist_ok=True)
        temp = raw_dir / f"{chunk_id}.partial"
        digest = hashlib.sha256()
        size = 0
        with self.session.get(BASE + "timeseries.get_range", params=request, auth=(self.key, ""), timeout=(10, 600), stream=True) as r:
            if r.status_code != 200:
                self._log({"event": "FAILED", "chunk_id": chunk_id, "at": _now(), "http_status": r.status_code})
                raise CreditGuard(f"timeseries HTTP {r.status_code} for {chunk_id}; reservation kept for review")
            with temp.open("wb") as out:
                for block in r.iter_content(1 << 20):
                    out.write(block)
                    digest.update(block)
                    size += len(block)
                    if size > 4 * q["billable_bytes"] + (64 << 20):
                        raise CreditGuard("response exceeded byte budget")
        raw = raw_dir / f"{chunk_id}.csv.zst"
        temp.replace(raw)
        record = {"event": "COMPLETED", "chunk_id": chunk_id, "at": _now(), "raw_file": str(raw.relative_to(self.root)),
                  "raw_sha256": digest.hexdigest(), "compressed_bytes": size, "quoted_cost_usd": q["cost_usd"],
                  "quoted_records": q["record_count"], "request": params}
        self._log(record)
        return {**record, "reused": False}


def read_chunk(path):
    import zstandard
    with open(path, "rb") as handle:
        data = zstandard.ZstdDecompressor().stream_reader(handle).read()
    return pd.read_csv(io.BytesIO(data))


def validate_ohlcv(frame, definitions=None):
    """Structural checks on authentic 1-minute bars; returns (clean frame, report)."""
    report = {"rows": int(len(frame))}
    required = {"ts_event", "instrument_id", "open", "high", "low", "close", "volume", "symbol"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"unexpected Databento schema: missing {sorted(missing)}")
    frame = frame.copy()
    frame["ts_event"] = pd.to_datetime(frame.ts_event, utc=True)
    frame["root"] = frame.symbol.str.split(".").str[0]
    report["symbols"] = frame.symbol.value_counts().to_dict()
    report["minute_aligned"] = bool((frame.ts_event == frame.ts_event.dt.floor("min")).all())
    dup = frame.duplicated(["symbol", "ts_event"])
    report["duplicates"] = int(dup.sum())
    bad = (frame.high < frame[["open", "close", "low"]].max(axis=1)) | (frame.low > frame[["open", "close", "high"]].min(axis=1))
    report["ohlc_inconsistent"] = int(bad.sum())
    tick = frame.root.map(TICK)
    off_tick = sum(((frame[c] / tick).round(6) % 1 != 0).sum() for c in ("open", "high", "low", "close"))
    report["off_tick_prices"] = int(off_tick)
    report["nonpositive_volume"] = int((frame.volume <= 0).sum())
    report["instruments"] = int(frame.instrument_id.nunique())
    if definitions is not None:
        known = set(definitions.instrument_id)
        report["unknown_instrument_ids"] = int((~frame.instrument_id.isin(known)).sum())
    clean = frame[~dup & ~bad].sort_values(["symbol", "ts_event"]).reset_index(drop=True)
    report["clean_rows"] = int(len(clean))
    return clean, report
