from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.auction.volume_profile import build_bar_approximation
from nocturne.instruments import get_instrument
from nocturne.strategies.value_rejection import ValueRejection
from nocturne.strategies.vwap_pullback import VWAPPullback

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


def test_vwap_pullback_generates_long_signal():
    closes = [100.0, 100.2, 100.4, 100.6, 100.8, 101.0, 101.2, 101.4]
    rows = []
    for i, close in enumerate(closes):
        ts = START + timedelta(minutes=5 * i)
        rows.append(bar(ts, close - 0.1, close + 0.3, close - 0.3, close))
    pullback = bar(START + timedelta(minutes=40), 101.4, 101.6, 100.8, 101.3)
    rows.append(pullback)
    signals = VWAPPullback().signals(pd.DataFrame(rows), NQ, DAY)
    assert len(signals) == 1
    assert signals[0].side == "LONG"


def test_vwap_pullback_no_signal_in_downtrend():
    closes = [105.0 - 0.3 * i for i in range(10)]
    rows = []
    for i, close in enumerate(closes):
        ts = START + timedelta(minutes=5 * i)
        rows.append(bar(ts, close, close + 0.2, close - 0.2, close))
    assert VWAPPullback().signals(pd.DataFrame(rows), NQ, DAY) == []


def test_value_rejection_generates_short():
    prior_bars = pd.DataFrame(
        [
            bar(START - timedelta(days=1), 101, 102, 100, 101, 1000),
        ]
    )
    prior = build_bar_approximation(prior_bars, "NQ", NQ.tick_size)
    current = pd.DataFrame([bar(START, 101, 103, 101, 101.5, 500)])
    signals = ValueRejection().signals(current, NQ, DAY, prior_profile=prior)
    assert len(signals) == 1
    assert signals[0].side == "SHORT"
