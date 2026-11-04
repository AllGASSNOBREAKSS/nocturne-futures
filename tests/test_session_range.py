import numpy as np
import pandas as pd

from nocturne.research.session_range import expanding_quantile_backtest, summarize


def ranges(count=40, seed=7):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"day": pd.date_range("2026-01-01", periods=count).strftime("%Y-%m-%d"),
                         "range": rng.gamma(2.0, 60.0, count)})


def test_expanding_quantiles_never_use_same_day_or_future():
    frame = ranges()
    summary = expanding_quantile_backtest(frame, min_history=20)
    for quantile, entry in summary.items():
        assert entry["n"] == len(frame) - 20
        assert entry["rows"]["day"][0] == frame.day.iloc[20]
        # First prediction uses exactly the first 20 rows.
        assert entry["rows"]["predicted"][0] == np.quantile(frame.range.iloc[:20], float(quantile))


def test_summary_flags_insufficient_history():
    assert summarize(ranges(15))["status"] == "INSUFFICIENT_COMPLETE_SESSIONS"
    result = summarize(ranges(40))
    assert result["status"] == "RESEARCH_ONLY"
    assert result["complete_sessions"] == 40
    assert result["unconditional"]["0.9"] >= result["unconditional"]["0.5"]
