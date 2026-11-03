from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.instruments import get_instrument
from nocturne.research.intraday_features import build_signal_features

UTC = timezone.utc
NQ = get_instrument("NQ")
ES = get_instrument("ES")


def bar(ts, close, volume=100):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": close - 0.05,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "volume": volume,
    }


def make_bars(start, count, base):
    return [bar(start + timedelta(minutes=5 * i), base + i * 0.1) for i in range(count)]


def frames():
    prior = pd.DataFrame(make_bars(datetime(2026, 10, 30, 13, 30, tzinfo=UTC), 78, 100))
    overnight = pd.DataFrame(make_bars(datetime(2026, 11, 1, 23, 0, tzinfo=UTC), 100, 101))
    rth = pd.DataFrame(make_bars(datetime(2026, 11, 2, 14, 30, tzinfo=UTC), 78, 102))
    nq = pd.concat([prior, overnight, rth], ignore_index=True)
    nq = add_session_column(nq, NQ)
    es = pd.DataFrame(make_bars(datetime(2026, 11, 2, 14, 30, tzinfo=UTC), 78, 200))
    es = add_session_column(es, ES)
    vix = pd.DataFrame(
        {"date": ["2026-10-29", "2026-10-30"], "close": [19.0, 20.0]}
    )
    return nq, es, vix


def test_features_are_point_in_time():
    nq, es, vix = frames()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    first = build_signal_features("test", asof, nq, es, vix, NQ)
    assert first
    assert first["profile_method"] == "BAR_APPROXIMATION"
    assert first["event_data_available"] is False
    assert np.isfinite(first["atr_pct"])
    assert np.isfinite(first["dist_vwap_atr"])
    assert first["vix_level"] == 20.0

    # Adding future bars must not change any feature.
    future = pd.DataFrame(
        make_bars(datetime(2026, 11, 2, 17, 0, tzinfo=UTC), 20, 200)
    )
    future = add_session_column(future, NQ)
    extended = pd.concat([nq, future], ignore_index=True)
    second = build_signal_features("test", asof, extended, es, vix, NQ)
    assert first.keys() == second.keys()
    for key in first:
        a, b = first[key], second[key]
        if isinstance(a, float) and np.isnan(a):
            assert isinstance(b, float) and np.isnan(b)
        else:
            assert a == b


def test_prior_session_levels_are_used():
    nq, es, vix = frames()
    features = build_signal_features(
        "test", datetime(2026, 11, 2, 16, 0, tzinfo=UTC), nq, es, vix, NQ
    )
    assert np.isfinite(features["dist_prior_high_atr"])
    assert np.isfinite(features["dist_prior_low_atr"])
    assert np.isfinite(features["dist_overnight_high_atr"])
