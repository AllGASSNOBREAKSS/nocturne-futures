"""Strategy contracts shared by all executable research rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TargetSpec:
    label: str
    price: float
    r_multiple: float


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    strategy_version: str
    instrument_id: str
    asof: datetime
    side: str  # LONG or SHORT
    entry_low: float
    entry_high: float
    stop: float
    targets: tuple[TargetSpec, ...]
    horizon_bars: int
    reason_codes: tuple[str, ...]
    data_requirements: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.side not in ("LONG", "SHORT"):
            raise ValueError("side must be LONG or SHORT")
        if self.entry_low > self.entry_high:
            raise ValueError("entry_low must be <= entry_high")
        if self.side == "LONG" and self.stop >= self.entry_low:
            raise ValueError("LONG stop must be below entry")
        if self.side == "SHORT" and self.stop <= self.entry_high:
            raise ValueError("SHORT stop must be above entry")


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    version: str
    instrument_id: str
    session: str
    entry_rule: str
    stop_rule: str
    target_rule: str
    horizon_bars: int
    event_gate: str
    data_requirements: tuple[str, ...]
