"""Authenticated raw-contract OHLCV downloads; no synthetic tick/order-flow data.

HTTP reference: https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range
Only one explicit contract per request. License/entitlement is the caller's
responsibility; availability is not inferred from an API key being present.
"""
import hashlib
import io
import json
import os
from pathlib import Path

import pandas as pd
import requests
import numpy as np

from .history import checksum, ingest_export


class DatabentoBars:
    def __init__(self, key=None, transport=None):
        self.key = key or os.environ.get("DATABENTO_API_KEY")
        self.transport = transport or requests.Session()

    def download(self, root, *, contract, instrument, start, end, license_scope,
                 dataset="GLBX.MDP3"):
        if not self.key:
            raise ValueError("DATA_BLOCKED: DATABENTO_API_KEY missing")
        if not contract or any(c in contract for c in (",", ".", "/", "\\")):
            raise ValueError("one explicit raw contract required")
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("ordered timezone-aware boundaries required")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        manifests = []
        while start < end:
            stop = min(start + pd.Timedelta("1D"), end)
            request = dict(dataset=dataset, symbols=contract, schema="ohlcv-1m",
                           stype_in="raw_symbol", start=start.isoformat(), end=stop.isoformat(),
                           encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true")
            identity = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            receipt = root / f"{identity}.json"
            if receipt.exists():
                record = json.loads(receipt.read_text())
                if record["license_scope"] != license_scope or record["instrument"] != instrument:
                    raise ValueError("conflicting request provenance")
                if checksum(root / record["raw_file"]) != record["raw_sha256"]:
                    raise ValueError("download checksum mismatch")
                if checksum(root / record["export_file"]) != record["export_sha256"]:
                    raise ValueError("export checksum mismatch")
            else:
                response = self.transport.get("https://hist.databento.com/v0/timeseries.get_range",
                                              params=request, auth=(self.key, ""), timeout=(10, 120))
                if response.status_code != 200:
                    raise RuntimeError(f"Databento HTTP {response.status_code}; request not checkpointed")
                frame = normalize_csv(response.content, contract, start, stop)
                raw = root / f"{identity}.csv"
                raw.write_bytes(response.content)
                export = root / f"{identity}.normalized.csv"
                frame.to_csv(export, index=False, lineterminator="\n")
                record = {"request": request, "raw_file": raw.name, "raw_sha256": checksum(raw),
                          "export_file": export.name, "export_sha256": checksum(export),
                          "instrument": instrument, "license_scope": license_scope,
                          "rows": len(frame), "received_at": pd.Timestamp.now(tz="UTC").isoformat(),
                          "availability": "bar-end lower bound; historical dissemination latency unknown"}
                if len(frame):
                    record["ingestion"] = ingest_export(export, root / "store", provider="databento",
                        instrument=instrument, interval="1min", price_basis="raw_contract", license_scope=license_scope)
                temporary = receipt.with_suffix(".tmp")
                temporary.write_text(json.dumps(record, indent=2) + "\n")
                temporary.replace(receipt)
            manifests.append(record)
            start = stop
        return manifests


def normalize_csv(payload, contract, start, end):
    frame = pd.read_csv(io.BytesIO(payload))
    required = {"ts_event", "open", "high", "low", "close", "volume"}
    if required - set(frame):
        raise ValueError("unexpected Databento OHLCV schema")
    if "symbol" in frame and not frame.symbol.eq(contract).all():
        raise ValueError("contract mismatch")
    if "instrument_id" in frame and frame.instrument_id.nunique() > 1:
        raise ValueError("raw-contract request returned multiple instruments")
    frame = frame.rename(columns={"ts_event": "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    if not ((frame.timestamp >= start) & (frame.timestamp < end)).all():
        raise ValueError("records outside requested interval")
    frame["available_at"] = frame.timestamp + pd.Timedelta("1min")
    frame["contract_id"] = contract
    prices = frame[["open", "high", "low", "close"]].to_numpy(float)
    volume = pd.to_numeric(frame.volume, errors="coerce").to_numpy(float)
    if (not np.isfinite(prices).all() or (prices <= 0).any()
            or not np.isfinite(volume).all() or (volume < 0).any()
            or frame.timestamp.duplicated().any()
            or (frame.high < frame[["open", "low", "close"]].max(axis=1)).any()
            or (frame.low > frame[["open", "high", "close"]].min(axis=1)).any()):
        raise ValueError("invalid raw contract OHLCV observations")
    return frame[["timestamp", "available_at", "open", "high", "low", "close", "volume", "contract_id"]]


def aggregate_five_minutes(frame):
    """Complete, aligned minute grids only; never aggregate across contracts."""
    frame = frame.copy()
    for col in ("timestamp", "available_at"):
        frame[col] = pd.to_datetime(frame[col], utc=True)
    if frame.duplicated(["contract_id", "timestamp"]).any():
        raise ValueError("duplicate contract timestamps")
    rows = []
    for (contract, start), group in frame.groupby(["contract_id", frame.timestamp.dt.floor("5min")]):
        group = group.sort_values("timestamp")
        if len(group) != 5 or not (pd.DatetimeIndex(group.timestamp) == pd.date_range(start, periods=5, freq="1min")).all():
            continue
        rows.append(dict(timestamp=start, available_at=max(group.available_at.max(), start + pd.Timedelta("5min")),
                         open=group.open.iloc[0], high=group.high.max(), low=group.low.min(),
                         close=group.close.iloc[-1], volume=group.volume.sum(), contract_id=contract))
    return pd.DataFrame(rows)
