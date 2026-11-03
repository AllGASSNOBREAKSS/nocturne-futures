"""Point-in-time economic-event storage and critical-day rules.

No provider is scraped. The default file is an explicitly labelled public
schedule sample with null consensus/actual values. Production adapters must
supply authorized, point-in-time records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CALENDAR_PATH = ROOT / "data" / "macro" / "sample_events.json"
UTC = timezone.utc


class EconomicEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    country: str = "US"
    event_type: str
    scheduled_at: datetime
    available_at: datetime
    consensus: float | None = None
    actual: float | None = None
    prior: float | None = None
    revised_prior: float | None = None
    source: str
    importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    instruments: list[str] = Field(default_factory=list)
    quality: Literal["SCHEDULED", "CONFIRMED", "PRELIMINARY", "UNAVAILABLE"] = "SCHEDULED"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class CalendarStore:
    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_CALENDAR_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def all(self) -> list[EconomicEvent]:
        if not self.path.exists():
            return []
        return [
            EconomicEvent.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, event: EconomicEvent) -> None:
        if any(item.event_id == event.event_id for item in self.all()):
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def upcoming(self, asof: datetime, horizon_hours: int = 24) -> list[EconomicEvent]:
        asof = _utc(asof)
        end = asof + timedelta(hours=horizon_hours)
        return sorted(
            [event for event in self.all() if asof <= _utc(event.scheduled_at) <= end],
            key=lambda event: _utc(event.scheduled_at),
        )

    def recent(self, asof: datetime, lookback_hours: int = 24) -> list[EconomicEvent]:
        asof = _utc(asof)
        start = asof - timedelta(hours=lookback_hours)
        return sorted(
            [
                event
                for event in self.all()
                if start <= _utc(event.available_at) <= asof
            ],
            key=lambda event: _utc(event.available_at),
        )

    def event_risk(self, asof: datetime, horizon_hours: int = 24) -> dict:
        events = self.upcoming(asof, horizon_hours)
        high = [event for event in events if event.importance == "HIGH"]
        return {
            "event_count": len(events),
            "high_impact_count": len(high),
            "next_event": events[0].model_dump(mode="json") if events else None,
            "high_impact_events": [event.model_dump(mode="json") for event in high],
        }


def load_sample_calendar() -> CalendarStore:
    return CalendarStore(DEFAULT_CALENDAR_PATH)


@dataclass(frozen=True)
class CriticalDayState:
    asof: str
    state: str
    reasons: tuple[str, ...]
    events: tuple[dict, ...]
    directional_bias: None = None
    data_quality: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def detect_critical_day(
    calendar: CalendarStore,
    asof: datetime,
    overnight_gap_atr: float | None = None,
    vix_level: float | None = None,
    atr_percentile: float | None = None,
) -> CriticalDayState:
    asof = _utc(asof)
    events = calendar.upcoming(asof, 24)
    high = [event for event in events if event.importance == "HIGH"]
    minutes = [
        (_utc(event.scheduled_at) - asof).total_seconds() / 60.0 for event in high
    ]
    within_hour = [event for event, delta in zip(high, minutes) if 0 <= delta <= 60]
    stress = (
        (overnight_gap_atr is not None and overnight_gap_atr >= 1.5)
        or (vix_level is not None and vix_level >= 25.0)
        or (atr_percentile is not None and atr_percentile >= 0.90)
    )

    reasons: list[str] = []
    if not calendar.all():
        state = "DATA_UNAVAILABLE"
        reasons.append("NO_AUTHORIZED_CALENDAR")
    elif within_hour:
        state = "PRE_EVENT_LOCK"
        reasons.append("HIGH_IMPACT_EVENT_WITHIN_60M")
    elif high:
        state = "SCHEDULED_HIGH_IMPACT"
        reasons.append("HIGH_IMPACT_EVENT_WITHIN_24H")
    elif stress:
        state = "LIQUIDITY_STRESS"
        reasons.append("OVERNIGHT_GAP_OR_VOLATILITY_STRESS")
    else:
        state = "NORMAL"
    if stress and state != "LIQUIDITY_STRESS":
        reasons.append("STRESS_OVERLAY")
    if overnight_gap_atr is not None:
        reasons.append(f"overnight_gap_atr={overnight_gap_atr:.2f}")
    if vix_level is not None:
        reasons.append(f"vix_level={vix_level:.2f}")

    return CriticalDayState(
        asof=asof.isoformat(),
        state=state,
        reasons=tuple(reasons),
        events=tuple(event.model_dump(mode="json") for event in high),
        directional_bias=None,
        data_quality={
            "calendar_source": str(calendar.path),
            "event_count": len(events),
            "high_impact_count": len(high),
            "point_in_time": True,
            "directional_bias_defined": False,
        },
    )


__all__ = [
    "DEFAULT_CALENDAR_PATH",
    "EconomicEvent",
    "CalendarStore",
    "CriticalDayState",
    "load_sample_calendar",
    "detect_critical_day",
]
