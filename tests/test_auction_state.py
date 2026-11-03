from datetime import datetime, timedelta, timezone

import pandas as pd

from nocturne.auction.state import (
    classify_acceptance,
    classify_balance,
    classify_value_migration,
    value_overlap,
)
from nocturne.auction.volume_profile import Trade, build_volume_profile

UTC = timezone.utc
BASE = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)


def profile(price: float, qty: float = 100):
    return build_volume_profile(
        [Trade(price, qty, BASE, BASE, trade_id=f"t-{price}")],
        "NQ",
        tick_size=1.0,
    )


def test_balance_classification():
    assert classify_balance(10, 20, 0.8) == "BALANCED"
    assert classify_balance(30, 20, 0.2) == "IMBALANCED"
    assert classify_balance(20, 20, 0.5) == "TRANSITION"


def test_acceptance_and_rejection():
    above = pd.DataFrame({"close": [101] * 6})
    assert classify_acceptance(above, 100, "ABOVE", min_bars=6) == "ACCEPTED"

    rejected = pd.DataFrame({"close": [101, 101, 101, 99, 99, 99]})
    assert classify_acceptance(rejected, 100, "ABOVE", min_bars=6) == "REJECTED"


def test_value_migration_rising_and_falling():
    prior = profile(100)
    higher = profile(102)
    lower = profile(98)
    assert classify_value_migration(prior, higher) == "RISING"
    assert classify_value_migration(prior, lower) == "FALLING"


def test_value_overlap_is_bounded():
    a = profile(100)
    b = profile(100)
    assert value_overlap(a, b) == 1.0
