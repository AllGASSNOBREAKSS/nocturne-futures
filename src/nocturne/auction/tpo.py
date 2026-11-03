"""TPO / Market Profile. Time-at-price is not traded volume-at-price."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .volume_profile import _bin_index, _tie_break_poc, _value_area


@dataclass
class TPOProfile:
    instrument_id: str
    session_type: str
    tick_size: float
    bin_ticks: int
    bins: dict[int, int]
    total_tpo: int
    poc_bin: int
    vah_bin: int
    val_bin: int
    bracket_minutes: int
    asof: datetime
    method: str = "TPO"

    def price_of_bin(self, bin_index: int) -> float:
        return round(bin_index * self.bin_ticks * self.tick_size, 10)

    @property
    def tpo_poc(self) -> float:
        return self.price_of_bin(self.poc_bin)

    @property
    def tpo_vah(self) -> float:
        return self.price_of_bin(self.vah_bin)

    @property
    def tpo_val(self) -> float:
        return self.price_of_bin(self.val_bin)


def build_tpo_profile(
    bars: pd.DataFrame,
    instrument_id: str,
    tick_size: float,
    session_type: str = "RTH",
    bin_ticks: int = 1,
    bracket_minutes: int = 30,
    value_area_share: float = 0.70,
    asof: datetime | None = None,
) -> TPOProfile:
    if bars.empty:
        raise ValueError("no bars for TPO")
    frame = bars
    if asof is not None:
        frame = frame[frame["available_at"] <= asof]
    if frame.empty:
        raise ValueError("no bars available at asof")

    frame = frame.sort_values("timestamp").copy()
    start = frame["timestamp"].iloc[0]
    frame["bracket"] = ((frame["timestamp"] - start).dt.total_seconds() // (bracket_minutes * 60)).astype(int)

    bins: dict[int, int] = {}
    for _, group in frame.groupby("bracket"):
        low_bin = _bin_index(float(group["low"].min()), tick_size, bin_ticks)
        high_bin = _bin_index(float(group["high"].max()), tick_size, bin_ticks)
        for idx in range(low_bin, high_bin + 1):
            bins[idx] = bins.get(idx, 0) + 1

    total = sum(bins.values())
    poc = _tie_break_poc({k: float(v) for k, v in bins.items()}, frame["close"].mean(), tick_size, bin_ticks)
    val, vah, _ = _value_area({k: float(v) for k, v in bins.items()}, poc, value_area_share)

    return TPOProfile(
        instrument_id=instrument_id,
        session_type=session_type,
        tick_size=tick_size,
        bin_ticks=bin_ticks,
        bins=bins,
        total_tpo=total,
        poc_bin=poc,
        vah_bin=vah,
        val_bin=val,
        bracket_minutes=bracket_minutes,
        asof=asof or max(frame["available_at"]),
    )
