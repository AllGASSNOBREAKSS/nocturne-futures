from datetime import datetime, timedelta, timezone

from nocturne.orderflow import (
    BookLevel,
    BookReconstructor,
    BookSnapshot,
    Quote,
    TradePrint,
    book_imbalance,
    classify_aggressor,
    cvd,
    feature_gate,
    footprint,
    validate_book,
)

UTC = timezone.utc
BASE = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)


def trade(price, qty, aggressor, minutes=0):
    return TradePrint(
        price=price,
        qty=qty,
        event_time=BASE + timedelta(minutes=minutes),
        available_at=BASE + timedelta(minutes=minutes),
        trade_id=f"t{minutes}",
        aggressor=aggressor,
        confidence=0.9,
    )


def test_aggressor_classification():
    assert classify_aggressor(101, 99, 101)[0] == "BUY"
    assert classify_aggressor(99, 99, 101)[0] == "SELL"
    assert classify_aggressor(100.5, 99, 101, prev_price=100)[0] == "BUY"
    assert classify_aggressor(100, 99, 101)[0] == "UNKNOWN"


def test_cvd_and_reset():
    trades = [trade(100, 10, "BUY", 0), trade(101, 5, "SELL", 20)]
    assert cvd(trades) == 5
    assert cvd(trades, reset_at=BASE + timedelta(minutes=10)) == -5


def test_footprint_separates_side():
    book = footprint([trade(100, 10, "BUY"), trade(100, 5, "SELL")], tick_size=0.25)
    bucket = int(round(100 / 0.25))
    assert book[bucket]["buy"] == 10
    assert book[bucket]["sell"] == 5


def test_feature_gate_blocks_without_data():
    gate = feature_gate(None, None)
    assert gate["available"] is False
    assert "NO_TICK_TRADES" in gate["reasons"]
    assert "NO_QUOTES" in gate["reasons"]


def test_book_validation_and_imbalance():
    crossed = BookSnapshot(bids=[BookLevel(101, 5)], asks=[BookLevel(100, 5)])
    assert "CROSSED_BOOK" in validate_book(crossed)
    normal = BookSnapshot(bids=[BookLevel(100, 10)], asks=[BookLevel(101, 5)])
    assert book_imbalance(normal) > 0


def test_reconstructor_handles_sequence_gap():
    book = BookReconstructor()
    book.apply_snapshot(
        BookSnapshot(bids=[BookLevel(100, 10)], asks=[BookLevel(101, 5)], sequence=1)
    )
    assert book.valid
    book.apply_delta("BID", 100, 0, sequence=2)
    assert 100 not in book.bids
    book.apply_delta("ASK", 101, 3, sequence=4)
    assert book.sequence_gaps == 1
    assert not book.valid
