"""Auction Market Theory state: balance, acceptance/rejection, value migration."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .volume_profile import VolumeProfile


@dataclass(frozen=True)
class AuctionState:
    state: str
    value_migration: str
    acceptance: str
    reasons: list[str] = field(default_factory=list)


def classify_balance(
    session_range: float,
    realized_range: float,
    value_overlap: float,
) -> str:
    """BALANCED / IMBALANCED / TRANSITION from range and value overlap."""
    if realized_range <= 0:
        return "TRANSITION"
    ratio = session_range / realized_range
    if ratio <= 0.8 and value_overlap >= 0.6:
        return "BALANCED"
    if ratio >= 1.2 or value_overlap <= 0.3:
        return "IMBALANCED"
    return "TRANSITION"


def classify_acceptance(
    bars: pd.DataFrame,
    level: float,
    side: str,
    min_bars: int = 6,
) -> str:
    """ACCEPTED / REJECTED / TESTING for a close beyond a level."""
    if bars.empty:
        return "TESTING"
    side = side.upper()
    if side == "ABOVE":
        beyond = bars["close"] > level
    elif side == "BELOW":
        beyond = bars["close"] < level
    else:
        raise ValueError("side must be ABOVE or BELOW")

    count = int(beyond.sum())
    last_beyond = bool(beyond.iloc[-1])
    if count >= min_bars and last_beyond:
        return "ACCEPTED"
    if count > 0 and not last_beyond:
        return "REJECTED"
    return "TESTING"


def value_overlap(prior: VolumeProfile, current: VolumeProfile) -> float:
    prior_lo, prior_hi = prior.val_bin, prior.vah_bin
    cur_lo, cur_hi = current.val_bin, current.vah_bin
    lo = max(prior_lo, cur_lo)
    hi = min(prior_hi, cur_hi)
    if hi < lo:
        return 0.0
    overlap = hi - lo + 1
    current_width = max(1, cur_hi - cur_lo + 1)
    return overlap / current_width


def classify_value_migration(prior: VolumeProfile, current: VolumeProfile) -> str:
    """RISING / FALLING / STABLE / MIXED from POC and value bounds."""
    if current.poc_bin > prior.poc_bin and current.val_bin >= prior.val_bin:
        return "RISING"
    if current.poc_bin < prior.poc_bin and current.vah_bin <= prior.vah_bin:
        return "FALLING"
    if value_overlap(prior, current) >= 0.6:
        return "STABLE"
    return "MIXED"


def classify_auction(
    session_range: float,
    realized_range: float,
    prior: VolumeProfile | None,
    current: VolumeProfile,
    bars: pd.DataFrame,
    reference_level: float | None = None,
) -> AuctionState:
    overlap = value_overlap(prior, current) if prior else 0.0
    state = classify_balance(session_range, realized_range, overlap)
    migration = classify_value_migration(prior, current) if prior else "UNKNOWN"
    if reference_level is None:
        reference_level = current.vah_price
    acceptance = classify_acceptance(bars, reference_level, "ABOVE")
    reasons = [
        f"range_ratio={session_range / realized_range:.2f}" if realized_range else "range_ratio=NA",
        f"value_overlap={overlap:.2f}",
        f"poc={current.poc_price:.2f}",
    ]
    return AuctionState(state=state, value_migration=migration, acceptance=acceptance, reasons=reasons)
