"""Backtesting package."""

from .engine import (
    BacktestConfig,
    BacktestReport,
    TradeResult,
    run_signal,
    run_signals,
    split_sessions,
)

__all__ = [
    "BacktestConfig",
    "BacktestReport",
    "TradeResult",
    "run_signal",
    "run_signals",
    "split_sessions",
]
