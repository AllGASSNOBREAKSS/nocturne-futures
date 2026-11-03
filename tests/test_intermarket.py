from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest
import pandas as pd

from nocturne.instruments import get_instrument
from nocturne.intermarket import build_intermarket_state
from nocturne.premarket import build_premarket_state

UTC = timezone.utc


def daily_frame(multiplier: float, n: int = 40) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=n, freq="B").strftime("%Y-%m-%d")
    rng = np.random.default_rng(3)
    returns = multiplier * (0.001 + rng.normal(0, 0.0002, n))
    base = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame({"date": dates, "close": base})


def test_intermarket_relative_and_proxy_flags():
    es = daily_frame(1.0)
    nq = daily_frame(2.0)
    vix = pd.DataFrame({"date": es["date"], "close": np.linspace(18, 22, len(es))})
    zn = daily_frame(-0.5)
    zb = daily_frame(-0.7)
    state = build_intermarket_state(es, nq, vix=vix, zn=zn, zb=zb, asof=es["date"].iloc[-1])
    assert state.relative_1d is not None
    assert state.beta_20d is not None and state.beta_20d > 1.5
    assert state.vix_proxy == "VIX_SPOT_PROXY"
    assert state.vx_futures_available is False
    assert "VX_FUTURES_UNAVAILABLE" in state.flags
    assert "ZN_ZB_YAHOO_PROXY" in state.flags
    assert state.zn_return_1d is not None


def bars(rows):
    return pd.DataFrame(
        rows,
        columns=["timestamp", "available_at", "open", "high", "low", "close", "volume"],
    )


def test_premarket_gap_and_leadership():
    nq_spec = get_instrument("NQ")
    es_spec = get_instrument("ES")
    nq = bars(
        [
            [datetime(2026, 10, 30, 14, 0, tzinfo=UTC), datetime(2026, 10, 30, 14, 5, tzinfo=UTC), 99, 100, 98, 99, 100],
            [datetime(2026, 11, 2, 2, 0, tzinfo=UTC), datetime(2026, 11, 2, 2, 5, tzinfo=UTC), 100, 101, 99.5, 100.5, 100],
        ]
    )
    es = bars(
        [
            [datetime(2026, 10, 30, 14, 0, tzinfo=UTC), datetime(2026, 10, 30, 14, 5, tzinfo=UTC), 99, 100, 98, 99, 100],
            [datetime(2026, 11, 2, 2, 0, tzinfo=UTC), datetime(2026, 11, 2, 2, 5, tzinfo=UTC), 99.5, 100.2, 99.6, 100.0, 100],
        ]
    )
    state = build_premarket_state(
        nq, es, nq_spec, es_spec, date(2026, 11, 2), datetime(2026, 11, 2, 12, 0, tzinfo=UTC), vix_level=21.0
    )
    assert state.nq_gap == pytest.approx(0.01515, abs=1e-4)
    assert state.es_gap == pytest.approx(0.01010, abs=1e-4)
    assert state.leadership == "NQ_LED"
    assert state.vix_state == "ELEVATED"
    assert state.data_quality["missing"] is False
    assert "CALENDAR_NOT_CONFIGURED" in state.flags


def test_premarket_marks_missing_intraday():
    empty = bars([])
    state = build_premarket_state(
        empty, empty, get_instrument("NQ"), get_instrument("ES"), date(2026, 11, 2), datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    )
    assert state.nq_gap is None
    assert state.data_quality["missing"] is True
    assert "INTRADAY_BARS_MISSING" in state.flags
