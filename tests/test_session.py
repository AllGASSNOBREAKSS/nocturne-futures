from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.auction.session import (
    developing_vwap,
    initial_balance,
    opening_range,
    session_bars,
    vwap,
)
from nocturne.instruments import get_instrument

UTC = timezone.utc
NQ = get_instrument("NQ")
DAY = date(2026, 11, 2)
RTH_START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def bars():
    rows = []
    for i in range(12):
        ts = RTH_START + timedelta(minutes=5 * i)
        rows.append(
            {
                "timestamp": ts,
                "available_at": ts + timedelta(minutes=5),
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100.5 + i,
                "volume": 100 + i,
            }
        )
    return pd.DataFrame(rows)


def test_session_bars_filters_rth():
    frame = bars()
    selected = session_bars(frame, NQ, "RTH", DAY)
    assert len(selected) == 12
    assert selected["timestamp"].iloc[0] == RTH_START


def test_initial_balance_first_60_minutes():
    ib = initial_balance(bars(), NQ, DAY, minutes=60)
    assert ib.high == 101 + 11
    assert ib.low == 99
    assert ib.complete


def test_opening_range_incomplete_before_end():
    asof = RTH_START + timedelta(minutes=10)
    window = opening_range(bars(), NQ, DAY, minutes=30, asof=asof)
    assert not window.complete


def test_vwap_and_developing_vwap():
    frame = bars()
    assert vwap(frame) > 0
    asof = RTH_START + timedelta(minutes=20)
    early = developing_vwap(frame, asof)
    full = vwap(frame)
    assert early != full
