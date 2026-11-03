from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from nocturne.regime import classify_regime
from nocturne.research.range_model import expected_range

UTC = timezone.utc


def make_bars(n=600, trend=0.1, noise=0.0, seed=7):
    rng = np.random.default_rng(seed)
    closes = 100 + np.arange(n) * trend + rng.normal(0, noise, n).cumsum()
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for i, close in enumerate(closes):
        ts = start + timedelta(minutes=5 * i)
        rows.append(
            {
                "timestamp": ts,
                "available_at": ts + timedelta(minutes=5),
                "open": close - 0.05,
                "high": close + 0.25,
                "low": close - 0.25,
                "close": close,
                "volume": 100,
            }
        )
    return pd.DataFrame(rows)


def test_range_quantiles_are_monotonic():
    bars = make_bars(600, trend=0.0, noise=0.5)
    forecast = expected_range(bars, horizon_bars=12, asof=bars["available_at"].iloc[-1])
    assert forecast.p50 <= forecast.p80 <= forecast.p90
    assert 0 <= forecast.p_ge_200 <= 1
    assert 0 <= forecast.p_ge_350 <= 1
    assert 0 <= forecast.p_ge_500 <= 1
    assert forecast.sample_n > 0


def test_range_does_not_use_future_bars():
    bars = make_bars(600, trend=0.0, noise=0.5)
    asof = bars["available_at"].iloc[300]
    first = expected_range(bars, horizon_bars=12, asof=asof)
    second = expected_range(bars.iloc[:301], horizon_bars=12, asof=asof)
    assert first.to_dict() == second.to_dict()


def test_regime_trend_and_probabilities():
    bars = make_bars(300, trend=0.2, noise=0.05)
    state = classify_regime(bars, asof=bars["available_at"].iloc[-1])
    assert state.label in {"TREND_UP", "EXPANSION", "STRESS"}
    if state.future_probabilities:
        assert abs(sum(state.future_probabilities.values()) - 1.0) < 0.01


def test_regime_choppy_is_not_trend():
    bars = make_bars(300, trend=0.0, noise=1.0)
    state = classify_regime(bars, asof=bars["available_at"].iloc[-1])
    assert state.label in {"BALANCED", "CHOP", "COMPRESSION", "EXPANSION", "TRANSITION"}
