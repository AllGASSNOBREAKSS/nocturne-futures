"""Tape and quote interfaces.

These are typed optional adapters. With no tick/quote history the feature gate
returns UNAVAILABLE; OHLCV is never relabelled as order flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TradePrint:
    price: float
    qty: float
    event_time: datetime
    available_at: datetime
    trade_id: str
    aggressor: str = "UNKNOWN"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise ValueError("qty must be positive")


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    event_time: datetime
    available_at: datetime
    source_seq: int | None = None

    def __post_init__(self) -> None:
        if self.bid > self.ask:
            raise ValueError("crossed quote")


def classify_aggressor(
    price: float,
    bid: float,
    ask: float,
    prev_price: float | None = None,
) -> tuple[str, float]:
    if price >= ask:
        return "BUY", 0.9
    if price <= bid:
        return "SELL", 0.9
    if prev_price is not None and price > prev_price:
        return "BUY", 0.6
    if prev_price is not None and price < prev_price:
        return "SELL", 0.6
    return "UNKNOWN", 0.0


def cvd(trades: list[TradePrint], reset_at: datetime | None = None) -> float:
    total = 0.0
    for trade in trades:
        if reset_at is not None and trade.event_time < reset_at:
            continue
        if trade.aggressor == "BUY":
            total += trade.qty
        elif trade.aggressor == "SELL":
            total -= trade.qty
    return total


def footprint(trades: list[TradePrint], tick_size: float) -> dict[int, dict[str, float]]:
    book: dict[int, dict[str, float]] = {}
    for trade in trades:
        bucket = int(round(trade.price / tick_size))
        entry = book.setdefault(bucket, {"buy": 0.0, "sell": 0.0, "unknown": 0.0})
        if trade.aggressor == "BUY":
            entry["buy"] += trade.qty
        elif trade.aggressor == "SELL":
            entry["sell"] += trade.qty
        else:
            entry["unknown"] += trade.qty
    return book


def feature_gate(trades: list[TradePrint] | None, quotes: list[Quote] | None) -> dict:
    reasons = []
    if not trades:
        reasons.append("NO_TICK_TRADES")
    if not quotes:
        reasons.append("NO_QUOTES")
    return {
        "available": not reasons,
        "cvd_available": bool(trades),
        "aggressor_confidence": "QUOTE_RULE" if quotes else "TICK_RULE_ONLY",
        "reasons": reasons,
    }
