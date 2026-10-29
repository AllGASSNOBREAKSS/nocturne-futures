"""Level utilities.

The published call records analyst-curated levels in `call.json`. The helpers
here are the transparent baseline used to generate candidate levels for the
next call: prior-session extremes, the overnight range, VWAP, and a one-ATR
envelope.
"""

from __future__ import annotations

import math

from .models import Instrument


def distance(price: float, level: float) -> float:
    """Positive means price is above the level."""
    return price - level


def nearest_level(price: float, levels: dict[str, float]) -> tuple[str, float, float]:
    name, value = min(levels.items(), key=lambda item: abs(price - item[1]))
    return name, value, price - value


def round_number_levels(price: float, step: float) -> tuple[float, float]:
    """Nearest round numbers strictly below and above the price."""
    below = math.floor(price / step) * step
    above = math.ceil(price / step) * step
    if math.isclose(below, price):
        below -= step
    if math.isclose(above, price):
        above += step
    return below, above


def level_book(inst: Instrument) -> dict[str, float]:
    half = inst.atr14 / 2.0
    return {
        "rth_high": inst.rth_high,
        "rth_low": inst.rth_low,
        "overnight_high": inst.overnight_high,
        "overnight_low": inst.overnight_low,
        "vwap": inst.vwap,
        "atr_upper": inst.last + half,
        "atr_lower": inst.last - half,
    }


def primary_levels(inst: Instrument) -> dict[str, float]:
    """Baseline five-level map: structural R1/S1, one ATR beyond for R2/S2."""
    half = inst.atr14 / 2.0
    r1 = max(inst.rth_high, inst.overnight_high)
    s1 = min(inst.rth_low, inst.overnight_low)
    return {
        "r2": round(r1 + half, 4),
        "r1": round(r1, 4),
        "pivot": round(inst.vwap, 4),
        "s1": round(s1, 4),
        "s2": round(s1 - half, 4),
    }


def level_breaks(high: float, low: float, levels: dict[str, float]) -> dict[str, float]:
    """How far the session ran past each level (positive = broken)."""
    return {
        "r2": high - levels["r2"],
        "r1": high - levels["r1"],
        "s1": levels["s1"] - low,
        "s2": levels["s2"] - low,
    }
