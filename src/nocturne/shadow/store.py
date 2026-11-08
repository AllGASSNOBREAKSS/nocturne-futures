"""Immutable shadow-forecast and outcome storage.

Forecasts are appended before outcomes exist. Conflicting rewrites of the same
forecast id are rejected, and outcomes are keyed by forecast id plus realized
range so a re-evaluation cannot silently replace a different result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path

from .locking import FileLock

UTC = timezone.utc


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def serialized(method):
    @wraps(method)
    def run(self, *args, **kwargs):
        with FileLock(self.root / ".store.lock"):
            return method(self, *args, **kwargs)
    return run


def _append(path, record):
    # Never repair/truncate a partial journal silently after a failed write.
    if path.exists():
        content = path.read_bytes()
        if content and not content.endswith(b"\n"):
            raise ValueError(f"incomplete journal; manual recovery required: {path.name}")
    with path.open("ab") as handle:
        handle.write((json.dumps(record, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


class ShadowStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.forecast_path = self.root / "forecasts.jsonl"
        self.outcome_path = self.root / "outcomes.jsonl"
        self.quality_path = self.root / "data_quality.jsonl"
        self.missed_path = self.root / "missed.jsonl"
        self.log_path = self.root / "log.jsonl"
        self.meta_path = self.root / "meta.json"
        self.alert_path = self.root / "alerts.jsonl"
        self.reconciliation_path = self.root / "reconciliations.jsonl"

    def forecasts(self) -> list[dict]:
        return _lines(self.forecast_path)

    def outcomes(self) -> list[dict]:
        return _lines(self.outcome_path)

    def quality_events(self) -> list[dict]:
        return _lines(self.quality_path)

    def missed(self) -> list[dict]:
        return _lines(self.missed_path)

    def log_events(self) -> list[dict]:
        return _lines(self.log_path)

    def alert_events(self) -> list[dict]:
        return _lines(self.alert_path)

    def reconciliations(self) -> list[dict]:
        return _lines(self.reconciliation_path)

    @serialized
    def append_reconciliation(self, record):
        from ..adapters.snapshots import canonical, digest
        identifier = digest(canonical(record))
        for previous in self.reconciliations():
            if previous["reconciliation_id"] == identifier:
                return previous
        stored = {**record, "reconciliation_id": identifier}
        _append(self.reconciliation_path, stored)
        return stored

    @serialized
    def sync_alerts(self, issues: dict, now: datetime, resolve_missing=True) -> list[dict]:
        """Append open/resolve transitions; never rewrite incident history."""
        latest = {item["key"]: item for item in self.alert_events()}
        written = []
        for key in sorted(set(latest) | set(issues)):
            state = "OPEN" if key in issues else "RESOLVED"
            if state == "RESOLVED" and not resolve_missing:
                continue
            previous = latest.get(key)
            if previous and previous["state"] == state:
                continue
            if not previous and state == "RESOLVED":
                continue
            record = {"key": key, "state": state, "at": now.astimezone(UTC).isoformat(),
                      "detail": issues.get(key, {}), "trading_decision": "NO_TRADE"}
            _append(self.alert_path, record)
            written.append(record)
        return written

    def meta(self) -> dict:
        if not self.meta_path.exists():
            return {}
        return json.loads(self.meta_path.read_text(encoding="utf-8"))

    @serialized
    def acknowledge_alert(self, key: str, actor: str, reason_code: str, now: datetime) -> dict:
        """Local operator acknowledgement, never resolution or a gate override.

        Use identifiers/reason codes only: do not submit secrets or free-form text.
        The latest state remains OPEN so existing monitors cannot lose the alert.
        """
        if (now.tzinfo is None or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', actor)
                or not re.fullmatch(r'[A-Z0-9_]{1,64}', reason_code)):
            raise ValueError('aware time, bounded actor identifier and reason code required')
        latest = {item['key']: item for item in self.alert_events()}.get(key)
        if latest is None or latest['state'] != 'OPEN':
            raise ValueError('only an existing open alert can be acknowledged')
        if datetime.fromisoformat(latest['at']) > now:
            raise ValueError('acknowledgement cannot precede the latest alert event')
        acknowledgement = {'actor': actor, 'reason_code': reason_code}
        if latest.get('acknowledgement') == acknowledgement:
            return latest
        record = {**latest, 'at': now.astimezone(UTC).isoformat(), 'state': 'OPEN',
                  'event': 'ACKNOWLEDGED', 'acknowledgement': acknowledgement}
        _append(self.alert_path, record)
        return record

    @serialized
    def ensure_started(self, now: datetime, model_id: str) -> dict:
        """Record the first service start once; never overwrite it."""
        meta = self.meta()
        if meta:
            return meta
        meta = {"service_start": now.astimezone(UTC).isoformat(), "model_id": model_id,
                "schema": 1}
        with self.meta_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(meta, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return meta

    @serialized
    def append_missed(self, record: dict) -> dict:
        required = {"target_date", "recorded_at", "reason"}
        missing = required - set(record)
        if missing:
            raise ValueError(f"missing missed-forecast fields: {sorted(missing)}")
        for item in self.missed():
            if item["target_date"] == record["target_date"]:
                return item
        _append(self.missed_path, record)
        return record

    @serialized
    def log(self, event: str, level: str = "INFO", detail: dict | None = None,
            now: datetime | None = None) -> dict:
        record = {"at": (now or datetime.now(UTC)).isoformat(), "level": level,
                  "event": event, "detail": detail or {}}
        _append(self.log_path, record)
        return record

    def latest(self) -> dict | None:
        records = self.forecasts()
        return records[-1] if records else None

    @serialized
    def append_forecast(self, record: dict) -> dict:
        required = {"forecast_id", "model_id", "target_date", "data_date", "created_at",
                    "quantiles", "features", "feature_digest"}
        missing = required - set(record)
        if missing:
            raise ValueError(f"missing forecast fields: {sorted(missing)}")
        if record["quantiles"].get("p50") is None or record["quantiles"].get("p90") is None:
            raise ValueError("forecast quantiles incomplete")
        if not (record["quantiles"]["p50"] <= record["quantiles"]["p80"] <= record["quantiles"]["p90"]):
            raise ValueError("quantiles must be monotone")
        existing = {item["forecast_id"]: item for item in self.forecasts()}
        if record["forecast_id"] in existing:
            previous = existing[record["forecast_id"]]
            stable = ("model_id", "target_date", "data_date", "reference_close",
                      "quantiles", "feature_digest")
            if any(previous.get(field) != record.get(field) for field in stable):
                raise ValueError("conflicting immutable forecast")
            # Idempotent retry: keep the original creation timestamp.
            return previous
        scope = lambda item: tuple(item.get(k) for k in ("model_id", "instrument", "kind", "target_date"))
        if any(scope(item) == scope(record) for item in existing.values()):
            raise ValueError("forecast already issued for model/instrument/horizon/date")
        _append(self.forecast_path, record)
        return record

    @serialized
    def append_outcome(self, record: dict) -> dict:
        required = {"forecast_id", "evaluated_at", "realized_range_pct", "covered"}
        missing = required - set(record)
        if missing:
            raise ValueError(f"missing outcome fields: {sorted(missing)}")
        key = record["forecast_id"]
        for item in self.outcomes():
            if item["forecast_id"] == key:
                if {k: v for k, v in item.items() if k != "evaluated_at"} != {
                    k: v for k, v in record.items() if k != "evaluated_at"
                }:
                    raise ValueError("conflicting outcome for forecast")
                return item
        _append(self.outcome_path, record)
        return record

    @serialized
    def record_quality_failure(self, reason: str, detail: dict | None = None) -> dict:
        record = {"at": datetime.now(UTC).isoformat(), "reason": reason, "detail": detail or {}}
        _append(self.quality_path, record)
        return record


def forecast_id(model_id: str, target_date: str, feature_digest: str) -> str:
    return hashlib.sha256(f"{model_id}|{target_date}|{feature_digest}".encode()).hexdigest()[:24]
