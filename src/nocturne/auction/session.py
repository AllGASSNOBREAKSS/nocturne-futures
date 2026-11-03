"""Session filtering, opening range, initial balance and VWAP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from ..instruments import InstrumentSpec
from ..market_clock import session_window


@dataclass(frozen=True)
class RangeWindow:
    high: float
    low: float
    start: datetime
    end: datetime
    complete: bool

    @property
    def width(self) -> float:
        return self.high - self.low


def session_bars(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    session: str,
    day: date,
) -> pd.DataFrame:
    window = session_window(spec, session, day)
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    mask = (frame["timestamp"] >= window.start_utc) & (frame["timestamp"] < window.end_utc)
    return frame.loc[mask].sort_values("timestamp").reset_index(drop=True)


def window_range(
    bars: pd.DataFrame,
    start: datetime,
    end: datetime,
    asof: datetime | None = None,
) -> RangeWindow:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    subset = frame[(frame["timestamp"] >= start) & (frame["timestamp"] < end)]
    if subset.empty:
        raise ValueError("no bars in range window")
    complete = asof is None or asof >= end
    return RangeWindow(
        high=float(subset["high"].max()),
        low=float(subset["low"].min()),
        start=start,
        end=end,
        complete=complete,
    )


def opening_range(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    day: date,
    minutes: int = 30,
    asof: datetime | None = None,
) -> RangeWindow:
    window = session_window(spec, "RTH", day)
    return window_range(bars, window.start_utc, window.start_utc + timedelta(minutes=minutes), asof)


def initial_balance(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    day: date,
    minutes: int = 60,
    asof: datetime | None = None,
) -> RangeWindow:
    window = session_window(spec, "RTH", day)
    return window_range(bars, window.start_utc, window.start_utc + timedelta(minutes=minutes), asof)


def vwap(bars: pd.DataFrame) -> float:
    if bars.empty:
        raise ValueError("no bars for VWAP")
    typical = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    volume = bars["volume"].astype(float)
    total = float(volume.sum())
    if total <= 0:
        raise ValueError("zero volume for VWAP")
    return float((typical * volume).sum() / total)


def developing_vwap(bars: pd.DataFrame, asof: datetime) -> float:
    frame = bars.copy()
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    return vwap(frame[frame["available_at"] <= asof])
