"""Volume-at-price, POC, value area and HVN/LVN.

True volume profile requires executed trades with quantity. A bar-derived
profile is supported for demos but is always labelled `BAR_APPROXIMATION` and
must never be presented as exchange-accurate volume-at-price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Trade:
    price: float
    qty: float
    event_time: datetime
    available_at: datetime
    trade_id: str
    aggressor: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("trade qty must be positive")


@dataclass
class VolumeProfile:
    instrument_id: str
    session_type: str
    tick_size: float
    bin_ticks: int
    bins: dict[int, float]
    total_volume: float
    poc_bin: int
    vah_bin: int
    val_bin: int
    hvn_bins: tuple[int, ...]
    lvn_bins: tuple[int, ...]
    vwap: float
    asof: datetime
    method: str = "TRADED_VOLUME"
    quality: str = "OK"
    value_area_share: float = 0.70

    def price_of_bin(self, bin_index: int) -> float:
        return round(bin_index * self.bin_ticks * self.tick_size, 10)

    @property
    def poc_price(self) -> float:
        return self.price_of_bin(self.poc_bin)

    @property
    def vah_price(self) -> float:
        return self.price_of_bin(self.vah_bin)

    @property
    def val_price(self) -> float:
        return self.price_of_bin(self.val_bin)

    @property
    def value_area_volume(self) -> float:
        return sum(self.bins.get(i, 0.0) for i in range(self.val_bin, self.vah_bin + 1))


def _bin_index(price: float, tick_size: float, bin_ticks: int) -> int:
    tick = int(math.floor(price / tick_size + 1e-9))
    return tick // bin_ticks


def _tie_break_poc(bins: dict[int, float], vwap_price: float, tick_size: float, bin_ticks: int) -> int:
    max_volume = max(bins.values())
    candidates = [b for b, v in bins.items() if abs(v - max_volume) < 1e-12]
    if len(candidates) == 1:
        return candidates[0]
    # Deterministic: nearest to VWAP, then lower bin.
    return min(candidates, key=lambda b: (abs(b * bin_ticks * tick_size - vwap_price), b))


def _value_area(
    bins: dict[int, float], poc: int, share: float
) -> tuple[int, int, float]:
    total = sum(bins.values())
    target = total * share
    lo = hi = poc
    included_volume = bins[poc]
    min_bin, max_bin = min(bins), max(bins)

    while included_volume < target and (lo > min_bin or hi < max_bin):
        below = bins.get(lo - 1, 0.0) if lo > min_bin else -1.0
        above = bins.get(hi + 1, 0.0) if hi < max_bin else -1.0
        if above > below:
            hi += 1
            included_volume += above
        elif below > above:
            lo -= 1
            included_volume += below
        else:
            # Tie: compare the next bin on each side, then default lower.
            below2 = bins.get(lo - 2, 0.0) if lo - 1 > min_bin else -1.0
            above2 = bins.get(hi + 2, 0.0) if hi + 1 < max_bin else -1.0
            if above2 > below2:
                hi += 1
                included_volume += above
            else:
                lo -= 1
                included_volume += below
    return lo, hi, included_volume


def _smooth(values: list[float], window: int) -> list[float]:
    if window <= 1 or len(values) < window:
        return values
    half = window // 2
    out = []
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def _nodes(
    bins: dict[int, float], window: int, prominence: float
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if not bins:
        return (), ()
    lo, hi = min(bins), max(bins)
    grid = [bins.get(i, 0.0) for i in range(lo, hi + 1)]
    smooth = _smooth(grid, window)
    peak = max(smooth) if smooth else 0.0
    if peak <= 0:
        return (), ()
    threshold = peak * prominence
    hvn: list[int] = []
    lvn: list[int] = []
    for i in range(1, len(smooth) - 1):
        if smooth[i] >= threshold and smooth[i] > smooth[i - 1] and smooth[i] >= smooth[i + 1]:
            hvn.append(lo + i)
        if smooth[i] <= threshold and smooth[i] < smooth[i - 1] and smooth[i] <= smooth[i + 1]:
            lvn.append(lo + i)
    return tuple(hvn), tuple(lvn)


def build_volume_profile(
    trades: Iterable[Trade],
    instrument_id: str,
    tick_size: float,
    session_type: str = "RTH",
    bin_ticks: int = 1,
    value_area_share: float = 0.70,
    asof: datetime | None = None,
    hvn_window: int = 3,
    hvn_prominence: float = 0.35,
) -> VolumeProfile:
    eligible = [t for t in trades if asof is None or t.available_at <= asof]
    if not eligible:
        raise ValueError("no eligible trades for profile")

    bins: dict[int, float] = {}
    total_qty = 0.0
    notional = 0.0
    for trade in eligible:
        idx = _bin_index(trade.price, tick_size, bin_ticks)
        bins[idx] = bins.get(idx, 0.0) + trade.qty
        total_qty += trade.qty
        notional += trade.price * trade.qty

    vwap = notional / total_qty
    poc = _tie_break_poc(bins, vwap, tick_size, bin_ticks)
    val, vah, _ = _value_area(bins, poc, value_area_share)
    hvn, lvn = _nodes(bins, hvn_window, hvn_prominence)

    quality = "OK" if len(eligible) >= 10 else "INSUFFICIENT_TRADES"
    return VolumeProfile(
        instrument_id=instrument_id,
        session_type=session_type,
        tick_size=tick_size,
        bin_ticks=bin_ticks,
        bins=bins,
        total_volume=total_qty,
        poc_bin=poc,
        vah_bin=vah,
        val_bin=val,
        hvn_bins=hvn,
        lvn_bins=lvn,
        vwap=round(vwap, 10),
        asof=asof or max(t.available_at for t in eligible),
        method="TRADED_VOLUME",
        quality=quality,
        value_area_share=value_area_share,
    )


def build_bar_approximation(
    bars: pd.DataFrame,
    instrument_id: str,
    tick_size: float,
    session_type: str = "RTH",
    bin_ticks: int = 1,
    value_area_share: float = 0.70,
    asof: datetime | None = None,
) -> VolumeProfile:
    """Distribute each bar's volume uniformly across its high-low range.

    This is an approximation for demos only. It is not traded volume-at-price.
    """
    if bars.empty:
        raise ValueError("no bars for profile")
    frame = bars
    if asof is not None:
        frame = frame[frame["available_at"] <= asof]
    if frame.empty:
        raise ValueError("no bars available at asof")

    bins: dict[int, float] = {}
    total_volume = 0.0
    for row in frame.itertuples(index=False):
        low_bin = _bin_index(float(row.low), tick_size, bin_ticks)
        high_bin = _bin_index(float(row.high), tick_size, bin_ticks)
        width = max(1, high_bin - low_bin + 1)
        share = float(row.volume) / width
        for idx in range(low_bin, high_bin + 1):
            bins[idx] = bins.get(idx, 0.0) + share
        total_volume += float(row.volume)

    if total_volume <= 0:
        raise ValueError("bars have no volume")

    vwap = float((frame["close"] * frame["volume"]).sum() / total_volume)
    poc = _tie_break_poc(bins, vwap, tick_size, bin_ticks)
    val, vah, _ = _value_area(bins, poc, value_area_share)
    hvn, lvn = _nodes(bins, 3, 0.35)
    return VolumeProfile(
        instrument_id=instrument_id,
        session_type=session_type,
        tick_size=tick_size,
        bin_ticks=bin_ticks,
        bins=bins,
        total_volume=total_volume,
        poc_bin=poc,
        vah_bin=vah,
        val_bin=val,
        hvn_bins=hvn,
        lvn_bins=lvn,
        vwap=round(vwap, 10),
        asof=asof or max(frame["available_at"]),
        method="BAR_APPROXIMATION",
        quality="APPROXIMATION",
        value_area_share=value_area_share,
    )


def composite_profile(
    profiles: list[VolumeProfile],
    instrument_id: str,
    session_type: str = "COMPOSITE",
) -> VolumeProfile:
    if not profiles:
        raise ValueError("no profiles")
    bins: dict[int, float] = {}
    for profile in profiles:
        for idx, volume in profile.bins.items():
            bins[idx] = bins.get(idx, 0.0) + volume
    total = sum(bins.values())
    vwap = sum(p.vwap * p.total_volume for p in profiles) / total
    poc = _tie_break_poc(bins, vwap, profiles[0].tick_size, profiles[0].bin_ticks)
    val, vah, _ = _value_area(bins, poc, profiles[0].value_area_share)
    hvn, lvn = _nodes(bins, 3, 0.35)
    return VolumeProfile(
        instrument_id=instrument_id,
        session_type=session_type,
        tick_size=profiles[0].tick_size,
        bin_ticks=profiles[0].bin_ticks,
        bins=bins,
        total_volume=total,
        poc_bin=poc,
        vah_bin=vah,
        val_bin=val,
        hvn_bins=hvn,
        lvn_bins=lvn,
        vwap=vwap,
        asof=max(p.asof for p in profiles),
        method="TRADED_VOLUME",
        quality="OK",
    )
