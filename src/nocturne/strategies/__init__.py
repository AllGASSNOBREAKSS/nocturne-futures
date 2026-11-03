"""Executable strategy candidates."""

from .base import Signal, StrategySpec, TargetSpec
from .opening_range import OpeningRangeBreakout
from .value_rejection import ValueRejection
from .vwap_pullback import VWAPPullback

__all__ = [
    "Signal",
    "StrategySpec",
    "TargetSpec",
    "OpeningRangeBreakout",
    "VWAPPullback",
    "ValueRejection",
]
