"""Empirical reachability for significant price levels.

The estimate answers a narrow question: given the current ATR-normalized
distance to a level, how often did a comparable historical setup touch that
level within the horizon? It is **not** a target-before-stop probability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from ..market_clock import ensure_utc


@dataclass(frozen=True)
class TouchProbability:
    level: float
    asof: str
    horizon_bars: int
    direction: str
    distance_atr: float
    probability: float | None
    sample_n: int
    tolerance_atr: float
    method: str

    def to_dict(self) -> dict:
        return asdict(self)


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def estimate_touch_probability(
    bars: pd.DataFrame,
    level: float,
    horizon_bars: int = 78,
    asof: datetime | None = None,
    tolerance_atr: float = 0.25,
    min_samples: int = 20,
) -> TouchProbability:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    if asof is not None:
        frame = frame[frame["available_at"] <= ensure_utc(asof)].reset_index(drop=True)
    if len(frame) < horizon_bars + 20:
        raise ValueError("not enough bars for reachability")

    atr = _atr(frame)
    current_atr = float(atr.iloc[-1])
    if not np.isfinite(current_atr) or current_atr <= 0:
        raise ValueError("invalid current ATR")
    current_close = float(frame["close"].iloc[-1])
    direction = "ABOVE" if level > current_close else "BELOW"
    current_distance = abs(level - current_close) / current_atr

    highs = frame["high"].to_numpy()
    lows = frame["low"].to_numpy()
    closes = frame["close"].to_numpy()
    atrs = atr.to_numpy()

    def sample(tolerance: float) -> tuple[list[bool], int]:
        touched = []
        for index in range(len(frame) - horizon_bars):
            atr_i = atrs[index]
            if not np.isfinite(atr_i) or atr_i <= 0:
                continue
            distance = (level - closes[index]) / atr_i
            if direction == "ABOVE" and distance <= 0:
                continue
            if direction == "BELOW" and distance >= 0:
                continue
            if abs(abs(distance) - current_distance) > tolerance:
                continue
            end = index + 1 + horizon_bars
            if direction == "ABOVE":
                touched.append(bool(highs[index + 1 : end].max() >= level))
            else:
                touched.append(bool(lows[index + 1 : end].min() <= level))
        return touched, len(touched)

    touched, count = sample(tolerance_atr)
    used_tolerance = tolerance_atr
    method = "EMPIRICAL_FORWARD_MFE"
    if count < min_samples:
        touched, count = sample(max(tolerance_atr, 0.75))
        used_tolerance = max(tolerance_atr, 0.75)
        method = "EMPIRICAL_FORWARD_MFE_WIDENED"
    if count < min_samples:
        return TouchProbability(
            level=round(float(level), 4),
            asof=str(asof or frame["available_at"].iloc[-1]),
            horizon_bars=horizon_bars,
            direction=direction,
            distance_atr=round(current_distance, 4),
            probability=None,
            sample_n=count,
            tolerance_atr=used_tolerance,
            method="INSUFFICIENT_COMPARABLE_HISTORY",
        )
    return TouchProbability(
        level=round(float(level), 4),
        asof=str(asof or frame["available_at"].iloc[-1]),
        horizon_bars=horizon_bars,
        direction=direction,
        distance_atr=round(current_distance, 4),
        probability=round(float(np.mean(touched)), 4),
        sample_n=count,
        tolerance_atr=used_tolerance,
        method=method,
    )


__all__ = ["TouchProbability", "estimate_touch_probability"]
