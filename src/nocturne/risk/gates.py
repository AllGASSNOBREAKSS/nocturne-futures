"""Deterministic risk and data gates. Default to NO_TRADE when unsure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..contracts import Decision, Quality, RiskDecision
from ..market_clock import ensure_utc


@dataclass(frozen=True)
class RiskConfig:
    max_staleness_seconds: int = 90_000  # 25 hours
    min_coverage: float = 0.95
    event_lock_minutes: int = 30
    max_atr_percentile: float = 0.98


@dataclass(frozen=True)
class RiskContext:
    now: datetime
    watermark: datetime
    coverage: float = 1.0
    critical_day_state: str = "NORMAL"
    minutes_to_event: int | None = None
    atr_percentile: float | None = None
    market_open: bool = True
    signal_expires_at: datetime | None = None
    duplicate: bool = False
    expected_value_points: float | None = None


def evaluate_risk(context: RiskContext, config: RiskConfig | None = None) -> RiskDecision:
    config = config or RiskConfig()
    now = ensure_utc(context.now)
    watermark = ensure_utc(context.watermark)
    reasons: list[str] = []

    if not context.market_open:
        reasons.append("MARKET_CLOSED")
    if (now - watermark).total_seconds() > config.max_staleness_seconds:
        reasons.append("STALE_DATA")
    if context.coverage < config.min_coverage:
        reasons.append("LOW_COVERAGE")
    if context.critical_day_state in {"DATA_UNRELIABLE", "HALTED_OR_CLOSED"}:
        reasons.append(f"STATE_{context.critical_day_state}")
    if context.minutes_to_event is not None and 0 <= context.minutes_to_event <= config.event_lock_minutes:
        reasons.append("PRE_EVENT_LOCK")
    if context.atr_percentile is not None and context.atr_percentile > config.max_atr_percentile:
        reasons.append("EXTREME_VOLATILITY")
    if context.signal_expires_at is not None and now > ensure_utc(context.signal_expires_at):
        reasons.append("SIGNAL_EXPIRED")
    if context.duplicate:
        reasons.append("DUPLICATE_SIGNAL")
    if context.expected_value_points is not None and context.expected_value_points < 0:
        reasons.append("NEGATIVE_EV")

    allow = not reasons
    return RiskDecision(
        decision=Decision.WAIT if allow else Decision.NO_TRADE,
        reason_codes=reasons,
        critical_day_state=context.critical_day_state,
        data_quality=Quality(coverage=context.coverage),
        allow_new_risk=allow,
    )
