"""Exchange sessions, DST-safe UTC windows, holidays and roll dates.

The calendar is an engineering baseline. Production must use provider-authoritative
CME/CFE/CBOT calendars; the values here are documented and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .instruments import InstrumentSpec

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

# US equity-market holidays, 2025-2027. Good Friday is included because CME
# equity index futures close; Treasury futures have a different calendar.
HOLIDAYS: set[date] = {
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
    date(2025, 5, 26), date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1),
    date(2025, 11, 27), date(2025, 12, 25),
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 11, 26), date(2026, 12, 25),
    date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 3, 26),
    date(2027, 5, 31), date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6),
    date(2027, 11, 25), date(2027, 12, 24),
}

RTH_HOURS = {
    "CME_EQUITY_INDEX": (time(9, 30), time(16, 0)),
    "CFE_VX": (time(9, 30), time(16, 15)),
    "CBOT_TREASURY": (time(8, 20), time(15, 0)),
}


@dataclass(frozen=True)
class SessionWindow:
    session: str
    session_date: date
    start_utc: datetime
    end_utc: datetime

    def contains(self, ts: datetime) -> bool:
        ts = ensure_utc(ts)
        return self.start_utc <= ts < self.end_utc


def ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def to_et(ts: datetime) -> datetime:
    return ensure_utc(ts).astimezone(ET)


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in HOLIDAYS


def next_trading_day(day: date) -> date:
    nxt = day + timedelta(days=1)
    while not is_trading_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def trading_days(start: date, end: date) -> list[date]:
    out: list[date] = []
    cur = start
    while cur <= end:
        if is_trading_day(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out


def _at(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=ET).astimezone(UTC)


def session_date(ts: datetime, spec: InstrumentSpec) -> date:
    """The RTH session date for an instant. After 18:00 ET counts as next day."""
    et = to_et(ts)
    if et.time() >= time(18, 0):
        return next_trading_day(et.date())
    return et.date()


def session_window(spec: InstrumentSpec, session: str, day: date) -> SessionWindow:
    session = session.upper()
    start_clock, end_clock = RTH_HOURS.get(spec.session_calendar, (time(9, 30), time(16, 0)))
    if session == "RTH":
        return SessionWindow("RTH", day, _at(day, start_clock), _at(day, end_clock))
    if session == "OVERNIGHT":
        prev = day - timedelta(days=1)
        return SessionWindow("OVERNIGHT", day, _at(prev, time(18, 0)), _at(day, start_clock))
    if session == "ETH":
        prev = day - timedelta(days=1)
        return SessionWindow("ETH", day, _at(prev, time(18, 0)), _at(day, time(17, 0)))
    raise ValueError(f"unknown session {session!r}")


def is_rth(ts: datetime, spec: InstrumentSpec) -> bool:
    day = session_date(ts, spec)
    return session_window(spec, "RTH", day).contains(ts)


def third_friday(year: int, month: int) -> date:
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7
    return first + timedelta(days=offset + 14)


def expiry_date(year: int, month: int) -> date:
    return third_friday(year, month)


def roll_date(year: int, month: int) -> date:
    """Approximate roll: seven calendar days before the third Friday."""
    return expiry_date(year, month) - timedelta(days=7)


def next_roll(spec: InstrumentSpec, asof: datetime) -> tuple[date, date]:
    """Return (expiry, roll) for the next contract month after asof."""
    day = to_et(asof).date()
    year = day.year
    for candidate_year in (year, year + 1):
        for month in sorted(spec.contract_months):
            exp = expiry_date(candidate_year, month)
            if exp > day:
                return exp, roll_date(candidate_year, month)
    raise RuntimeError("no roll date found")


def is_roll_window(spec: InstrumentSpec, asof: datetime, days: int = 5) -> bool:
    expiry, roll = next_roll(spec, asof)
    return 0 <= (expiry - to_et(asof).date()).days <= days
