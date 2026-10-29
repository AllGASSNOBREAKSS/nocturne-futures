import pandas as pd
import pytest

from nocturne.stats import atr, expected_move, realized_vol, summarize


def test_atr_matches_hand_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-06"],
            "high": [10.0, 12.0, 11.0, 13.0],
            "low": [8.0, 9.0, 9.0, 10.0],
            "close": [9.0, 11.0, 10.0, 12.0],
        }
    )
    # True ranges after the first bar: 3, 2, 3. ATR(3) = 8/3.
    assert atr(df, 3).iloc[-1] == pytest.approx(8 / 3)


def test_realized_vol_is_zero_for_constant_returns():
    close = pd.Series([100 * 1.01**i for i in range(21)])
    assert realized_vol(close, 20) == pytest.approx(0.0, abs=1e-9)


def test_summarize_reports_up_rate_and_average():
    stats = summarize([1.0, -1.0, 2.0], [2.0, 2.0, 2.0])
    assert stats["n"] == 3
    assert stats["pct_up"] == pytest.approx(66.7, abs=0.1)
    assert stats["avg_ret"] == pytest.approx(0.667, abs=0.001)
    assert stats["avg_range"] == pytest.approx(2.0)


def test_expected_move_uses_annualized_vol():
    # 16% annualized vol is roughly 1% per day.
    assert expected_move(100.0, 16.0) == pytest.approx(1.008, abs=0.01)
