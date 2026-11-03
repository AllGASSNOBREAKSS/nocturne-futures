from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.instruments import get_instrument
from nocturne.strategies.opening_range import OpeningRangeBreakout

UTC = timezone.utc
NQ = get_instrument("NQ")
DAY = date(2026, 11, 2)
START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def bar(ts, o, h, l, c, v=100):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def ib_bars():
    return [bar(START + timedelta(minutes=5 * i), 101, 102, 100, 101) for i in range(12)]


def test_orb_generates_long_signal_after_ib():
    bars = pd.DataFrame(ib_bars() + [bar(START + timedelta(minutes=60), 101, 103, 101.5, 103)])
    strategy = OpeningRangeBreakout(ib_minutes=60, buffer_ticks=2)
    signals = strategy.signals(bars, NQ, DAY)
    assert len(signals) == 1
    signal = signals[0]
    assert signal.side == "LONG"
    assert signal.stop == 100
    assert signal.targets[0].price == 106
    assert signal.targets[1].price == 109


def test_orb_waits_for_completed_ib():
    bars = pd.DataFrame([bar(START + timedelta(minutes=5 * i), 101, 103, 100, 103) for i in range(6)])
    strategy = OpeningRangeBreakout(ib_minutes=60)
    assert strategy.signals(bars, NQ, DAY) == []


def test_orb_short_signal():
    bars = pd.DataFrame(ib_bars() + [bar(START + timedelta(minutes=60), 101, 101, 98, 98.5)])
    strategy = OpeningRangeBreakout(ib_minutes=60, buffer_ticks=2)
    signals = strategy.signals(bars, NQ, DAY)
    assert len(signals) == 1
    assert signals[0].side == "SHORT"
    assert signals[0].stop == 102
