from datetime import date, datetime, timezone

import pytest

from nocturne.instruments import get_instrument
from nocturne.market_clock import is_roll_window, next_roll, roll_date

UTC = timezone.utc


def test_nq_december_roll():
    expiry, roll = next_roll(get_instrument("NQ"), datetime(2026, 11, 3, 15, 0, tzinfo=UTC))
    assert expiry == date(2026, 12, 18)
    assert roll == date(2026, 12, 11)


def test_zn_quarterly_roll():
    expiry, roll = next_roll(get_instrument("ZN"), datetime(2026, 11, 3, 15, 0, tzinfo=UTC))
    assert expiry == date(2026, 12, 18)
    assert roll == date(2026, 12, 11)


def test_roll_window_is_five_days_before_expiry():
    nq = get_instrument("NQ")
    assert is_roll_window(nq, datetime(2026, 12, 14, 15, 0, tzinfo=UTC), days=5)
    assert not is_roll_window(nq, datetime(2026, 12, 8, 15, 0, tzinfo=UTC), days=5)


def test_roll_date_is_before_expiry():
    assert roll_date(2026, 12) < date(2026, 12, 18)
