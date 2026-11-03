import numpy as np
import pandas as pd

from nocturne.research.features import FEATURE_COLUMNS, build_daily_features


def make_bars(n=120):
    rng = np.random.default_rng(11)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.004, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.004, n)))
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    )


def test_features_exist_and_are_finite_late():
    frame = build_daily_features(make_bars())
    late = frame.iloc[60:]
    assert late[FEATURE_COLUMNS].notna().all().all()
    assert frame["signal_index"].iloc[0] == 0


def test_features_do_not_use_future_bars():
    bars = make_bars(120)
    short = build_daily_features(bars.iloc[:80])
    full = build_daily_features(bars)
    pd.testing.assert_frame_equal(
        short[FEATURE_COLUMNS].reset_index(drop=True),
        full[FEATURE_COLUMNS].iloc[:80].reset_index(drop=True),
    )
