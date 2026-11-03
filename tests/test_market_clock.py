from datetime import date, datetime, timezone

import pytest

from nocturne.instruments import get_instrument
from nocturne.market_clock import (
    expiry_date,
    is_rth,
    is_trading_day,
    next_roll,
    roll_date,
    session_date,
    session_window,
    third_friday,
)

NQ = get_instrument("NQ")


def test_rth_window_before_dst_end():
    window = session_window(NQ, "RTH", date(2026, 10, 30))
    assert window.start_utc == datetime(2026, 10, 30, 13, 30, tzinfo=timezone.utc)
    assert window.end_utc == datetime(2026, 10, 30, 20, 0, tzinfo=timezone.utc)


def test_rth_window_after_dst_end():
    window = session_window(NQ, "RTH", date(2026, 11, 2))
    assert window.start_utc == datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc)
    assert window.end_utc == datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc)


def test_is_rth_handles_dst():
    assert is_rth(datetime(2026, 10, 30, 14, 0, tzinfo=timezone.utc), NQ)
    assert not is_rth(datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc), NQ)
    assert is_rth(datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc), NQ)


def test_session_date_rolls_after_1800_et():
    # 23:00 UTC on Nov 2 is 18:00 EST, so the next session is Nov 3.
    assert session_date(datetime(2026, 11, 2, 23, 0, tzinfo=timezone.utc), NQ) == date(2026, 11, 3)


def test_holiday_calendar():
    assert not is_trading_day(date(2026, 11, 26))  # Thanksgiving
    assert not is_trading_day(date(2026, 12, 25))
    assert is_trading_day(date(2026, 11, 2))


def test_third_friday_and_roll():
    assert third_friday(2026, 12) == date(2026, 12, 18)
    assert expiry_date(2026, 12) == date(2026, 12, 18)
    assert roll_date(2026, 12) == date(2026, 12, 11)


def test_next_roll_for_nq():
    expiry, roll = next_roll(NQ, datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc))
    assert expiry == date(2026, 12, 18)
    assert roll == date(2026, 12, 11)
