"""Immutable shadow-forecast and outcome storage.

Forecasts are appended before outcomes exist. Conflicting rewrites of the same
forecast id are rejected, and outcomes are keyed by forecast id plus realized
range so a re-evaluation cannot silently replace a different result.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ShadowStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.forecast_path = self.root / "forecasts.jsonl"
        self.outcome_path = self.root / "outcomes.jsonl"
        self.quality_path = self.root / "data_quality.jsonl"

    def forecasts(self) -> list[dict]:
        return _lines(self.forecast_path)

    def outcomes(self) -> list[dict]:
        return _lines(self.outcome_path)

    def quality_events(self) -> list[dict]:
        return _lines(self.quality_path)

    def latest(self) -> dict | None:
        records = self.forecasts()
        return records[-1] if records else None

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
        with self.forecast_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def append_outcome(self, record: dict) -> dict:
        required = {"forecast_id", "evaluated_at", "realized_range_pct", "covered"}
        missing = required - set(record)
        if missing:
            raise ValueError(f"missing outcome fields: {sorted(missing)}")
        key = record["forecast_id"]
        for item in self.outcomes():
            if item["forecast_id"] == key:
                if item != record:
                    raise ValueError("conflicting outcome for forecast")
                return item
        with self.outcome_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def record_quality_failure(self, reason: str, detail: dict | None = None) -> dict:
        record = {"at": datetime.now(UTC).isoformat(), "reason": reason, "detail": detail or {}}
        with self.quality_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record


def forecast_id(model_id: str, target_date: str, feature_digest: str) -> str:
    return hashlib.sha256(f"{model_id}|{target_date}|{feature_digest}".encode()).hexdigest()[:24]
