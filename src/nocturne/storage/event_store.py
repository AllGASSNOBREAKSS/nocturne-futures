"""Immutable, append-only JSONL event store with as-of replay.

Layout:
    data/events/<INSTRUMENT>/<YYYY-MM-DD>.jsonl

Each line is a canonical MarketEvent. Files are never rewritten. Replay filters
on `available_at_utc <= asof` and sorts by event time, sequence, and event id.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path

from ..contracts import MarketEvent
from ..market_clock import ensure_utc


class EventStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._seen: set[str] | None = None

    def _path(self, instrument_id: str, event_time: datetime) -> Path:
        stamp = ensure_utc(event_time).strftime("%Y-%m-%d")
        return self.root / instrument_id.upper() / f"{stamp}.jsonl"

    def _load_seen(self) -> set[str]:
        if self._seen is None:
            self._seen = set()
            if self.root.exists():
                for path in self.root.glob("*/*.jsonl"):
                    with path.open("r", encoding="utf-8") as handle:
                        for line in handle:
                            if not line.strip():
                                continue
                            try:
                                self._seen.add(json.loads(line)["event_id"])
                            except (KeyError, json.JSONDecodeError):
                                continue
        return self._seen

    def append(self, event: MarketEvent) -> Path:
        path = self._path(event.instrument_id, event.event_time_utc)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        if self._seen is not None:
            self._seen.add(event.event_id)
        return path

    def append_many(self, events: Iterable[MarketEvent], dedupe: bool = True) -> int:
        seen = self._load_seen() if dedupe else set()
        written = 0
        for event in events:
            if dedupe and event.event_id in seen:
                continue
            self.append(event)
            seen.add(event.event_id)
            written += 1
        return written

    def read(
        self,
        instrument_id: str,
        start: date | None = None,
        end: date | None = None,
    ) -> Iterator[MarketEvent]:
        directory = self.root / instrument_id.upper()
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.jsonl")):
            day = date.fromisoformat(path.stem)
            if start and day < start:
                continue
            if end and day > end:
                continue
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        yield MarketEvent.model_validate_json(line)

    def replay(
        self,
        instrument_id: str,
        asof: datetime,
        start: date | None = None,
        end: date | None = None,
    ) -> list[MarketEvent]:
        cutoff = ensure_utc(asof)
        events = [
            event
            for event in self.read(instrument_id, start=start, end=end)
            if ensure_utc(event.available_at_utc) <= cutoff
        ]
        return sorted(
            events,
            key=lambda e: (ensure_utc(e.event_time_utc), e.source_sequence or 0, e.event_id),
        )

    def watermark(self, instrument_id: str) -> datetime | None:
        latest: datetime | None = None
        for event in self.read(instrument_id):
            available = ensure_utc(event.available_at_utc)
            if latest is None or available > latest:
                latest = available
        return latest

    def count(self, instrument_id: str | None = None) -> int:
        total = 0
        pattern = "*/*.jsonl" if instrument_id is None else f"{instrument_id.upper()}/*.jsonl"
        for path in self.root.glob(pattern):
            with path.open("r", encoding="utf-8") as handle:
                total += sum(1 for line in handle if line.strip())
        return total
