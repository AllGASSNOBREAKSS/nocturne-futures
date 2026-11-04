"""Content-addressed source evidence. Mutable caches are not historical records."""
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

UTC = timezone.utc


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def immutable_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("immutable source object conflict")
        return
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


class SnapshotStore:
    def __init__(self, root):
        self.root = Path(root)

    def _object(self, checksum):
        if not isinstance(checksum, str) or len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
            raise ValueError("invalid content hash")
        return self.root / "objects" / checksum

    def read_object(self, checksum):
        content = self._object(checksum).read_bytes()
        if digest(content) != checksum:
            raise ValueError("source object checksum mismatch")
        return content

    def capture(self, raw, normalized, provenance, wire=None):
        from ..shadow.locking import FileLock
        with FileLock(self.root / "archive.lock"):
            if provenance["frequency"] != "1d" or not provenance["symbol"]:
                raise ValueError("invalid source identity")
            received = pd.Timestamp(provenance["received_at"])
            now = datetime.now(UTC)
            if received.tzinfo is None or received > now:
                raise ValueError("invalid source receipt time")
            # A canonical parsed payload is evidence, but not wire bytes.
            if wire is not None and json.loads(wire) != json.loads(raw):
                raise ValueError("wire and parsed payload disagree")
            self._verify_normalization(raw, normalized, provenance)
            manifest = {"schema": 1, "source": provenance, "raw_sha256": digest(raw),
                        "normalized_sha256": digest(normalized),
                        "wire_sha256": digest(wire) if wire is not None else None,
                        "archived_at": now.isoformat(), "quality": "HASH_VERIFIED_SOURCE_EVIDENCE"}
            for content in (raw, normalized, wire):
                if content is not None:
                    immutable_write(self._object(digest(content)), content)
            identifier = digest(canonical(manifest))
            immutable_write(self.root / "manifests" / f"{identifier}.json", canonical(manifest))
            # Append a linked revision record before publishing a new cache head.
            head = self.root / "heads" / (digest(provenance["symbol"].encode()) + ".json")
            if head.exists():
                previous = json.loads(head.read_text())
                old_manifest = self.manifest(previous["snapshot_id"])
                previous_received = pd.Timestamp(old_manifest["source"]["received_at"])
                if received < previous_received:
                    return identifier  # archival import must never regress a live head
                if received == previous_received and old_manifest["normalized_sha256"] != manifest["normalized_sha256"]:
                    raise ValueError("conflicting observations at the same receipt time")
                if old_manifest["normalized_sha256"] != manifest["normalized_sha256"]:
                    old = self.frame(previous["snapshot_id"])
                    new = pd.read_csv(io.BytesIO(normalized))
                    changes = compare_daily(old, new)
                    record = {"previous_snapshot_id": previous["snapshot_id"], "snapshot_id": identifier,
                              "recorded_at": now.isoformat(), "symbol": provenance["symbol"], **changes}
                    from ..shadow.store import _append
                    _append(self.root / "revisions.jsonl", record)
            head.parent.mkdir(parents=True, exist_ok=True)
            temporary = head.with_suffix(".tmp")
            temporary.write_bytes(canonical({"snapshot_id": identifier}))
            os.replace(temporary, head)
            return identifier

    def manifest(self, identifier):
        self._object(identifier)  # validate path component
        content = (self.root / "manifests" / f"{identifier}.json").read_bytes()
        if digest(content) != identifier:
            raise ValueError("snapshot manifest checksum mismatch")
        manifest = json.loads(content)
        for field in ("raw_sha256", "normalized_sha256", "wire_sha256"):
            if manifest.get(field):
                self.read_object(manifest[field])
        return manifest

    @staticmethod
    def _verify_normalization(raw, normalized, source):
        from .yahoo_history import _frame
        payload = json.loads(raw)
        meta = payload["chart"]["result"][0]["meta"]
        if meta["symbol"] != source["symbol"] or meta.get("dataGranularity") != "1d":
            raise ValueError("raw source identity/frequency mismatch")
        expected = _frame(payload, source["symbol"])
        supplied = pd.read_csv(io.BytesIO(normalized), float_precision="round_trip")
        if list(expected.date) != list(supplied.date):
            raise ValueError("raw/normalized dates disagree")
        for field in ("open", "high", "low", "close", "volume"):
            if not np.array_equal(expected[field].to_numpy(float), supplied[field].to_numpy(float)):
                raise ValueError(f"raw/normalized {field} disagree")
        numeric = supplied[["open", "high", "low", "close", "volume"]].to_numpy(float)
        if not np.isfinite(numeric).all() or (numeric[:, :4] <= 0).any() or (numeric[:, 4] < 0).any():
            raise ValueError("invalid market observations")
        for field in ("timestamp", "available_at"):
            if not pd.to_datetime(expected[field], utc=True).eq(pd.to_datetime(supplied[field], utc=True)).all():
                raise ValueError("raw/normalized timestamps disagree")
        if "source_complete" in supplied and not expected.source_complete.eq(supplied.source_complete).all():
            raise ValueError("raw/normalized completeness disagree")

    def frame(self, identifier):
        manifest = self.manifest(identifier)
        frame = pd.read_csv(io.BytesIO(self.read_object(manifest["normalized_sha256"])))
        for column in ("timestamp", "available_at"):
            frame[column] = pd.to_datetime(frame[column], utc=True)
        return frame


def compare_daily(old, new):
    """Exact comparisons, not a materiality waiver. Additions are not revisions."""
    if old.date.duplicated().any() or new.date.duplicated().any():
        raise ValueError("duplicate daily dates")
    a, b = old.set_index("date"), new.set_index("date")
    changes = []
    for day in sorted(set(a.index) & set(b.index)):
        fields = {}
        for field in ("timestamp", "available_at", "open", "high", "low", "close", "volume"):
            left, right = a.loc[day, field], b.loc[day, field]
            if field in {"timestamp", "available_at"}:
                left, right = pd.Timestamp(left).isoformat(), pd.Timestamp(right).isoformat()
            else:
                left, right = float(left), float(right)
            if left != right:
                fields[field] = {"original": left, "revised": right}
        if fields:
            changes.append({"date": str(day), "fields": fields})
    removed = sorted(set(a.index) - set(b.index))
    return {"classification": "SOURCE_REVISION_REQUIRES_REVIEW" if changes or removed else "NEW_OBSERVATIONS_ONLY",
            "changed_observations": changes, "removed_dates": removed,
            "added_dates": sorted(set(b.index) - set(a.index))}
