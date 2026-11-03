"""Market-by-price book reconstruction with explicit sequence-gap handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BookLevel:
    price: float
    qty: float


@dataclass
class BookSnapshot:
    bids: list[BookLevel] = field(default_factory=list)
    asks: list[BookLevel] = field(default_factory=list)
    sequence: int | None = None
    event_time: datetime | None = None
    available_at: datetime | None = None


def validate_book(snapshot: BookSnapshot) -> list[str]:
    errors = []
    if any(level.qty < 0 for level in snapshot.bids + snapshot.asks):
        errors.append("NEGATIVE_QTY")
    if snapshot.bids and snapshot.asks:
        if max(level.price for level in snapshot.bids) >= min(level.price for level in snapshot.asks):
            errors.append("CROSSED_BOOK")
    if not snapshot.bids and not snapshot.asks:
        errors.append("EMPTY_BOOK")
    return errors


def book_imbalance(snapshot: BookSnapshot, levels: int = 5) -> float:
    bids = sorted(snapshot.bids, key=lambda x: x.price, reverse=True)[:levels]
    asks = sorted(snapshot.asks, key=lambda x: x.price)[:levels]
    bid_qty = sum(level.qty for level in bids)
    ask_qty = sum(level.qty for level in asks)
    total = bid_qty + ask_qty
    return (bid_qty - ask_qty) / total if total > 0 else 0.0


class BookReconstructor:
    def __init__(self) -> None:
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.last_sequence: int | None = None
        self.valid = False
        self.sequence_gaps = 0

    def apply_snapshot(self, snapshot: BookSnapshot) -> None:
        self.bids = {level.price: level.qty for level in snapshot.bids if level.qty > 0}
        self.asks = {level.price: level.qty for level in snapshot.asks if level.qty > 0}
        self.last_sequence = snapshot.sequence
        self.valid = not validate_book(snapshot)

    def apply_delta(self, side: str, price: float, qty: float, sequence: int, reset: bool = False) -> None:
        if reset:
            self.bids.clear()
            self.asks.clear()
            self.last_sequence = None
            self.valid = False
        if self.last_sequence is not None:
            if sequence <= self.last_sequence:
                return
            if sequence > self.last_sequence + 1:
                self.sequence_gaps += 1
                self.valid = False
        self.last_sequence = sequence
        book = self.bids if side.upper() == "BID" else self.asks
        if qty <= 0:
            book.pop(price, None)
        else:
            book[price] = qty

    def snapshot(self) -> BookSnapshot:
        return BookSnapshot(
            bids=[BookLevel(price, qty) for price, qty in sorted(self.bids.items(), reverse=True)],
            asks=[BookLevel(price, qty) for price, qty in sorted(self.asks.items())],
            sequence=self.last_sequence,
        )
