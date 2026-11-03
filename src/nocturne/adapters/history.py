"""Content-addressed ingestion of authorized historical OHLCV exports.

Raw bytes are immutable; normalized chunks and provenance manifests are separate.
No inferred contract identifiers, back-adjustment or missing-bar filling.
CSV keeps this path usable without an optional Parquet runtime.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bar_quality(frame, interval="5min"):
    if pd.Timedelta(interval) <= pd.Timedelta(0):
        raise ValueError("interval must be positive")
    required = ["timestamp", "available_at", "open", "high", "low", "close", "volume"]
    if set(required) - set(frame):
        raise ValueError(f"missing bar columns: {sorted(set(required) - set(frame))}")
    frame = frame.copy()
    for col in required[:2]:
        frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")
    prices = frame[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    invalid = (~np.isfinite(prices).all(axis=1) | frame.timestamp.isna() | frame.available_at.isna()
               | (prices.volume < 0) | (prices.high < prices[["open", "close", "low"]].max(axis=1))
               | (prices.low > prices[["open", "close", "high"]].min(axis=1))
               | (frame.available_at < frame.timestamp + pd.Timedelta(interval)))
    stamps = frame.timestamp.dropna().drop_duplicates().sort_values()
    gaps = stamps.diff().dropna()
    keys = ["timestamp"] + (["contract_id"] if "contract_id" in frame else [])
    return {"rows": len(frame), "invalid_rows": int(invalid.sum()),
            "duplicate_keys": int(frame.duplicated(keys).sum()),
            "zero_volume_rows": int((prices.volume == 0).sum()),
            "first": stamps.min().isoformat() if len(stamps) else None,
            "last": stamps.max().isoformat() if len(stamps) else None,
            "gap_intervals": int((gaps > pd.Timedelta(interval)).sum()),
            "gap_definition": "elapsed gaps; includes closures, not an exchange missing-bar count",
            "contract_ids_available": bool("contract_id" in frame and frame.contract_id.notna().all()),
            "usable_rows": int((~invalid & ~frame.duplicated(keys)).sum())}


def ingest_export(source, root, *, provider, instrument, interval,
                  price_basis, license_scope):
    """Resumable by raw digest. Conflicting revisions are never silently replaced."""
    if price_basis not in {"raw_contract", "continuous_unadjusted", "back_adjusted", "unknown"}:
        raise ValueError("explicit price_basis required")
    if not provider or not license_scope:
        raise ValueError("provider and license_scope required")
    source, root = Path(source), Path(root)
    digest = checksum(source)
    manifest = root / "manifests" / f"{digest}.json"
    metadata = dict(provider=provider, instrument=instrument, interval=interval,
                    price_basis=price_basis, license_scope=license_scope)
    if manifest.exists():
        stored = json.loads(manifest.read_text())
        if any(stored[k] != v for k, v in metadata.items()):
            raise ValueError("same raw bytes with conflicting provenance")
        if checksum(root / stored["normalized_path"]) != stored["normalized_sha256"]:
            raise ValueError("normalized checksum mismatch")
        if checksum(root / "raw" / f"{digest}.csv") != digest:
            raise ValueError("raw checksum mismatch")
        return stored
    frame = pd.read_csv(source)
    quality = bar_quality(frame, interval)
    if quality["invalid_rows"]:
        raise ValueError(f"invalid bars: {quality['invalid_rows']}")
    if price_basis == "raw_contract" and not quality["contract_ids_available"]:
        raise ValueError("raw contracts require contract_id")
    for col in ("timestamp", "available_at"):
        frame[col] = pd.to_datetime(frame[col], utc=True)
    frame = frame.drop_duplicates()
    keys = ["timestamp"] + (["contract_id"] if "contract_id" in frame else [])
    if frame.duplicated(keys).any():
        raise ValueError("conflicting revisions within export")
    for other in (root / "manifests").glob("*.json"):
        prior = json.loads(other.read_text())
        if any(prior[k] != metadata[k] for k in ("provider", "instrument", "interval", "price_basis")):
            continue
        old = pd.read_csv(root / prior["normalized_path"])
        for col in ("timestamp", "available_at"):
            old[col] = pd.to_datetime(old[col], utc=True)
        combined = pd.concat([old, frame]).drop_duplicates()
        if combined.duplicated(keys).any():
            raise ValueError("overlapping export contains revisions; quarantine and review")
    for folder in ("raw", "normalized", "manifests"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "raw" / f"{digest}.csv").write_bytes(source.read_bytes())
    normalized = root / "normalized" / f"{digest}.csv"
    frame.sort_values(keys).to_csv(normalized, index=False)
    result = {**metadata, "raw_sha256": digest, "normalized_sha256": checksum(normalized),
              "normalized_path": normalized.relative_to(root).as_posix(), "quality": quality,
              "received_at": pd.Timestamp.now(tz="UTC").isoformat(),
              "availability_assumption": "export available_at; historical provider vintage unverified"}
    manifest.write_text(json.dumps(result, indent=2, default=bool) + "\n", encoding="utf-8")
    return result
