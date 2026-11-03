from datetime import datetime, timedelta, timezone

import pandas as pd

from nocturne.price_levels.reachability import estimate_touch_probability

UTC = timezone.utc


def make_bars(n=300):
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(n):
        ts = start + timedelta(minutes=5 * i)
        close = 100.0 if i % 2 == 0 else 101.0
        rows.append(
            {
                "timestamp": ts,
                "available_at": ts + timedelta(minutes=5),
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 100,
            }
        )
    return pd.DataFrame(rows)


def test_near_level_is_more_reachable_than_far_level():
    bars = make_bars()
    asof = bars["available_at"].iloc[-1]
    near = estimate_touch_probability(bars, 100.5, horizon_bars=12, asof=asof)
    far = estimate_touch_probability(bars, 110.0, horizon_bars=12, asof=asof)
    assert 0.0 <= near.probability <= 1.0
    assert near.sample_n > 0
    assert far.probability != far.probability or far.probability == 0.0
    assert near.probability >= far.probability if far.probability == far.probability else True


def test_reachability_does_not_use_future_bars():
    bars = make_bars()
    asof = bars["available_at"].iloc[200]
    first = estimate_touch_probability(bars, 100.5, horizon_bars=12, asof=asof)
    second = estimate_touch_probability(bars.iloc[:201], 100.5, horizon_bars=12, asof=asof)
    assert first.to_dict() == second.to_dict()
