"""Leak-safe daily features.

Every feature at row t uses only bars up to and including t. The target is
created separately from future bars.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(bars: pd.DataFrame) -> pd.Series:
    prev = bars["close"].shift(1)
    return pd.concat(
        [bars["high"] - bars["low"], (bars["high"] - prev).abs(), (bars["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)


def build_daily_features(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy().reset_index(drop=True)
    close = frame["close"].astype(float)
    ret1 = close.pct_change()
    tr = true_range(frame)
    atr14 = tr.rolling(14).mean()

    frame["ret1"] = ret1
    frame["ret5"] = close.pct_change(5)
    frame["ret20"] = close.pct_change(20)
    frame["atr14"] = atr14
    frame["atr_pct"] = atr14 / close
    frame["sma20_dist"] = close / close.rolling(20).mean() - 1.0
    frame["sma50_dist"] = close / close.rolling(50).mean() - 1.0
    frame["vol20"] = ret1.rolling(20).std() * np.sqrt(252)
    frame["range_pct"] = (frame["high"] - frame["low"]) / close
    frame["gap"] = frame["open"] / close.shift(1) - 1.0
    frame["signal_index"] = np.arange(len(frame))

    dow = pd.to_datetime(frame["date"]).dt.dayofweek
    for day in range(1, 5):
        frame[f"dow_{day}"] = (dow == day).astype(float)

    return frame


FEATURE_COLUMNS = [
    "ret1",
    "ret5",
    "ret20",
    "atr_pct",
    "sma20_dist",
    "sma50_dist",
    "vol20",
    "range_pct",
    "gap",
    "dow_1",
    "dow_2",
    "dow_3",
    "dow_4",
]
