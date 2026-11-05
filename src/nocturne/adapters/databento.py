"""Authenticated raw-contract OHLCV downloads; no synthetic tick/order-flow data.

HTTP reference: https://databento.com/docs/api-historical
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
                 dataset="GLBX.MDP3", quote=None, approval=None, max_response_bytes=16 * 1024 * 1024):
        from .databento_access import pilot_request, check_approval
        from .snapshots import canonical, digest, immutable_write
        from ..shadow.locking import FileLock
        from ..instruments import get_instrument
        from ..research.contract_targets import validate_contract_bars, ContractTargetConfig
        scope = pilot_request(contract, instrument, start, end)
        if dataset != scope["dataset"] or not isinstance(license_scope, str) or not license_scope.strip():
            raise ValueError("explicit GLBX.MDP3 license provenance required")
        if type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 64 * 1024 * 1024:
            raise ValueError("pilot response memory budget must be 1KB to 64MB")
        start, end = pd.Timestamp(scope["start"]), pd.Timestamp(scope["end"])
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        request = {**scope, "encoding": "csv", "pretty_px": "true", "pretty_ts": "true", "map_symbols": "true"}
        identity = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        receipt = root / f"{identity}.json"
        with FileLock(root / "locks" / f"{identity}.lock"):
            if receipt.exists():
                record = json.loads(receipt.read_text())
                if record["license_scope"] != license_scope or record["instrument"] != instrument or record["request"] != request:
                    raise ValueError("conflicting request provenance")
                if any(Path(record[field]).name != record[field] for field in ("raw_file", "export_file")):
                    raise ValueError("invalid receipt file path")
                if checksum(root / record["raw_file"]) != record["raw_sha256"]:
                    raise ValueError("download checksum mismatch")
                if checksum(root / record["export_file"]) != record["export_sha256"]:
                    raise ValueError("export checksum mismatch")
                return [record]
            if not self.key:
                raise ValueError("DATA_BLOCKED: DATABENTO_API_KEY missing")
            if quote is None or approval is None:
                raise ValueError("explicit quote and operator approval required before metered acquisition")
            permit = check_approval(quote, approval, scope, instrument)
            immutable_write(root / "approval_objects" / permit["approval_sha256"], canonical(approval))
            reservation = root / "consumption" / f"{permit['quote_id']}.json"
            # Streaming retries may incur repeated charges, including credits.
            # Reserve durably BEFORE the network; never retry an uncertain attempt.
            if reservation.exists():
                raise ValueError("consumption attempt already reserved; operator reconciliation required")
            immutable_write(reservation, canonical({**permit, "request": scope, "state": "RESERVED_BEFORE_NETWORK"}))
            raw_hash = None
            content = bytearray()
            try:
                response = self.transport.get("https://hist.databento.com/v0/timeseries.get_range",
                                              params=request, auth=(self.key, ""), timeout=(10, 120), stream=True)
                if response.status_code != 200:
                    if hasattr(response, "close"):
                        response.close()
                    raise RuntimeError(f"Databento HTTP {response.status_code}; request not checkpointed")
                try:
                    chunks = response.iter_content(65536) if hasattr(response, "iter_content") else [response.content]
                    for chunk in chunks:
                        if len(content) + len(chunk) > max_response_bytes:
                            content.extend(chunk[:max_response_bytes - len(content)])
                            raise ValueError("pilot response byte budget exceeded; review partial consumption")
                        content.extend(chunk)
                finally:
                    if hasattr(response, "close"):
                        response.close()
                body = bytes(content)
                raw_hash = digest(body)
                immutable_write(root / "objects" / raw_hash, body)
                frame = normalize_csv(body, contract, start, end, expected_instrument_id=permit["resolved_instrument_id"])
                validation = validate_contract_bars(frame, get_instrument(instrument), ContractTargetConfig(interval="1min", min_rows=1))
                if len(frame) != quote["record_count"]:
                    raise ValueError("quoted record count changed; provider revision review required")
                raw = root / f"{identity}.csv"
                immutable_write(raw, body)
                export = root / f"{identity}.normalized.csv"
                immutable_write(export, frame.to_csv(index=False, lineterminator="\n").encode())
                record = {"request": request, "raw_file": raw.name, "raw_sha256": checksum(raw),
                          "export_file": export.name, "export_sha256": checksum(export),
                          "instrument": instrument, "license_scope": license_scope,
                          "rows": len(frame), "received_at": pd.Timestamp.now(tz="UTC").isoformat(),
                          "availability": "bar-end lower bound; historical dissemination latency unknown",
                          "consumption": permit, "quote": quote, "validation": validation,
                          "response_bytes": len(body), "missing_minutes": int((end - start) / pd.Timedelta("1min")) - len(frame),
                          "grid_warning": "missing minute messages are not automatically exchange outages; calendar/no-trade evidence required"}
                if len(frame):
                    record["ingestion"] = ingest_export(export, root / "store", provider="databento",
                        instrument=instrument, interval="1min", price_basis="raw_contract", license_scope=license_scope)
                immutable_write(receipt, json.dumps(record, indent=2).encode() + b"\n")
                return [record]
            except Exception as exc:
                partial_hash = digest(bytes(content)) if content and raw_hash is None else None
                if partial_hash:
                    immutable_write(root / "partial_objects" / partial_hash, bytes(content))
                event = {"quote_id": permit["quote_id"], "request": scope, "status": "CONSUMPTION_REVIEW_REQUIRED",
                         "reason": type(exc).__name__, "raw_sha256": raw_hash, "partial_sha256": partial_hash}
                immutable_write(root / "consumption_events" / f"{digest(canonical(event))}.json", canonical(event))
                raise


def normalize_csv(payload, contract, start, end, expected_instrument_id=None):
    frame = pd.read_csv(io.BytesIO(payload))
    required = {"ts_event", "open", "high", "low", "close", "volume"}
    if required - set(frame):
        raise ValueError("unexpected Databento OHLCV schema")
    if "symbol" not in frame and expected_instrument_id is None:
        raise ValueError("contract identity requires a raw symbol or verified instrument-ID mapping")
    if "symbol" in frame and not frame.symbol.eq(contract).all():
        raise ValueError("contract mismatch")
    if "instrument_id" in frame and frame.instrument_id.nunique() > 1:
        raise ValueError("raw-contract request returned multiple instruments")
    if expected_instrument_id is not None and ("instrument_id" not in frame or not frame.instrument_id.eq(expected_instrument_id).all()):
        raise ValueError("provider instrument ID differs from quoted symbology")
    frame = frame.rename(columns={"ts_event": "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    if not ((frame.timestamp >= start) & (frame.timestamp < end)).all() or not frame.timestamp.eq(frame.timestamp.dt.floor("min")).all():
        raise ValueError("records outside requested interval")
    frame["available_at"] = frame.timestamp + pd.Timedelta("1min")
    frame["contract_id"] = contract
    prices = frame[["open", "high", "low", "close"]].to_numpy(float)
    volume = pd.to_numeric(frame.volume, errors="coerce").to_numpy(float)
    if (not np.isfinite(prices).all() or (prices <= 0).any()
            or not np.isfinite(volume).all() or (volume < 0).any() or (volume != np.floor(volume)).any()
            or frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing
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
