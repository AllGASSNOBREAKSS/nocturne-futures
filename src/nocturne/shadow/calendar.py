"""Bounded US cash-equity calendar; not a futures session calendar."""
from datetime import date, datetime, time, timezone

from ..market_clock import ET, is_trading_day

EARLY_CLOSES = {date(2025, 7, 3), date(2025, 11, 28), date(2025, 12, 24),
                date(2026, 11, 27), date(2026, 12, 24), date(2027, 11, 26)}


def supported(day):
    return 2025 <= day.year <= 2027


def session_close(day):
    if not supported(day) or not is_trading_day(day):
        raise ValueError("unsupported cash session")
    clock = time(13) if day in EARLY_CLOSES else time(16)
    return datetime.combine(day, clock, ET).astimezone(timezone.utc)
