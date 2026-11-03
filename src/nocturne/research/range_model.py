"""Empirical expected-range and large-move probabilities.

The distribution is conditional on the current ATR percentile bucket and is
measured only from bars available at the as-of timestamp.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from ..market_clock import ensure_utc


@dataclass
class RangeForecast:
    asof: str
    horizon_bars: int
    sample_n: int
    bucket: int
    bucket_n: int
    atr: float
    p50: float
    p80: float
    p90: float
    p_ge_200: float
    p_ge_350: float
    p_ge_500: float

    def to_dict(self) -> dict:
        return asdict(self)


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def expected_range(
    bars: pd.DataFrame,
    horizon_bars: int = 78,
    asof: datetime | None = None,
    thresholds: tuple[float, ...] = (200.0, 350.0, 500.0),
    buckets: int = 4,
) -> RangeForecast:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    if asof is not None:
        frame = frame[frame["available_at"] <= ensure_utc(asof)].reset_index(drop=True)
    if len(frame) < horizon_bars + 20:
        raise ValueError("not enough bars for range forecast")

    atr = _atr(frame)
    forward_ranges = []
    forward_atr = []
    for i in range(len(frame) - horizon_bars):
        window = frame.iloc[i + 1 : i + 1 + horizon_bars]
        forward_ranges.append(float(window["high"].max() - window["low"].min()))
        forward_atr.append(float(atr.iloc[i]))
    ranges = np.asarray(forward_ranges)
    atrs = np.asarray(forward_atr)
    valid = np.isfinite(atrs) & np.isfinite(ranges)
    ranges, atrs = ranges[valid], atrs[valid]
    if len(ranges) < 50:
        raise ValueError("not enough valid forward ranges")

    current_atr = float(atr.iloc[-1])
    percentile_edges = np.quantile(atrs, np.linspace(0, 1, buckets + 1))
    bucket = int(np.searchsorted(percentile_edges[1:-1], current_atr, side="right"))
    bucket_mask = (atrs >= percentile_edges[bucket]) & (
        atrs <= percentile_edges[bucket + 1] if bucket == buckets - 1 else atrs < percentile_edges[bucket + 1]
    )
    sample = ranges[bucket_mask]
    raw_bucket_n = int(len(sample))
    if len(sample) < 20:
        sample = ranges

    return RangeForecast(
        asof=str(asof or frame["available_at"].iloc[-1]),
        horizon_bars=horizon_bars,
        sample_n=int(len(sample)),
        bucket=bucket,
        bucket_n=raw_bucket_n,
        atr=round(current_atr, 4),
        p50=round(float(np.quantile(sample, 0.50)), 2),
        p80=round(float(np.quantile(sample, 0.80)), 2),
        p90=round(float(np.quantile(sample, 0.90)), 2),
        p_ge_200=round(float((sample >= thresholds[0]).mean()), 4),
        p_ge_350=round(float((sample >= thresholds[1]).mean()), 4),
        p_ge_500=round(float((sample >= thresholds[2]).mean()), 4),
    )
