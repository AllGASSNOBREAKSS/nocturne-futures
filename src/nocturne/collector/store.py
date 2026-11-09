"""Content-addressed raw archive, normalized tables and revision ledger.

Raw bytes are stored gzip-compressed under their SHA-256 and never rewritten.
Each (source, dataset) has an append-only manifest. A new normalized table is
compared row-by-row against the previous one on its key columns, so appended
observations and changed historical values (provider revisions) are counted
separately rather than silently overwritten.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue().encode()


class Archive:
    def __init__(self, root):
        self.root = Path(root)

    def _dir(self, source, dataset):
        if not source.replace("_", "").isalnum() or not dataset.replace("_", "").replace("-", "").isalnum():
            raise ValueError("source/dataset identifiers must be alphanumeric")
        path = self.root / source / dataset
        (path / "raw").mkdir(parents=True, exist_ok=True)
        return path

    def manifest(self, source, dataset):
        path = self._dir(source, dataset) / "manifest.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def latest(self, source, dataset):
        entries = [e for e in self.manifest(source, dataset) if e.get("normalized_sha256")]
        return entries[-1] if entries else None

    def load(self, source, dataset, entry=None):
        entry = entry or self.latest(source, dataset)
        if entry is None:
            return None
        path = self._dir(source, dataset) / "normalized" / f"{entry['normalized_sha256']}.csv"
        content = path.read_bytes()
        if sha256(content) != entry["normalized_sha256"]:
            raise ValueError(f"normalized checksum mismatch for {source}/{dataset}")
        return pd.read_csv(io.BytesIO(content))

    def record(self, source, dataset, raw: bytes, frame: pd.DataFrame, keys: list[str], meta: dict,
               value_columns: list[str] | None = None) -> dict:
        """Persist one acquisition; return the manifest entry (NEW/UNCHANGED/UPDATED)."""
        folder = self._dir(source, dataset)
        raw_digest = sha256(raw)
        raw_path = folder / "raw" / f"{raw_digest}.gz"
        if not raw_path.exists():
            raw_path.write_bytes(gzip.compress(raw, mtime=0))
        frame = frame.sort_values(keys).reset_index(drop=True)
        if frame.duplicated(keys).any():
            raise ValueError(f"duplicate keys in {source}/{dataset}")
        normalized = _csv_bytes(frame)
        norm_digest = sha256(normalized)
        (folder / "normalized").mkdir(exist_ok=True)
        norm_path = folder / "normalized" / f"{norm_digest}.csv"
        if not norm_path.exists():
            norm_path.write_bytes(normalized)
        previous = self.latest(source, dataset)
        comparison = {"appended_rows": len(frame), "removed_rows": 0, "revised_rows": 0, "revised_examples": []}
        if previous is not None and previous["normalized_sha256"] != norm_digest:
            old = self.load(source, dataset, previous)
            comparison = compare(old, frame, keys, value_columns)
        status = "NEW" if previous is None else "UNCHANGED" if previous["normalized_sha256"] == norm_digest else "UPDATED"
        entry = {"source": source, "dataset": dataset, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                 "status": status, "raw_sha256": raw_digest, "raw_bytes": len(raw),
                 "normalized_sha256": norm_digest, "rows": len(frame),
                 "previous_normalized_sha256": previous["normalized_sha256"] if previous else None,
                 **comparison, **meta}
        with (folder / "manifest.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str, sort_keys=True) + "\n")
        return entry


def compare(old: pd.DataFrame, new: pd.DataFrame, keys, value_columns=None) -> dict:
    old = old.copy()
    new = new.copy()
    for frame in (old, new):
        for key in keys:
            frame[key] = frame[key].astype(str)
    columns = value_columns or [c for c in new.columns if c not in keys and c in old.columns]
    merged = old.merge(new, on=keys, how="outer", suffixes=("_old", "_new"), indicator=True)
    both = merged[merged["_merge"] == "both"]
    revised = pd.Series(False, index=both.index)
    for column in columns:
        a, b = both[f"{column}_old"], both[f"{column}_new"]
        na, nb = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
        numeric = na.notna() & nb.notna()
        differs = (numeric & ((na - nb).abs() > 1e-9 * (1 + nb.abs()))) | \
                  (~numeric & (a.astype(str).fillna("") != b.astype(str).fillna("")))
        revised |= differs
    examples = both[revised].head(5)
    return {"appended_rows": int((merged["_merge"] == "right_only").sum()),
            "removed_rows": int((merged["_merge"] == "left_only").sum()),
            "revised_rows": int(revised.sum()),
            "revised_examples": [{k: row[k] for k in keys} for _, row in examples.iterrows()]}
