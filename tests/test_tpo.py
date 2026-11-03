from datetime import datetime, timedelta, timezone

import pandas as pd

from nocturne.auction.tpo import build_tpo_profile
from nocturne.auction.volume_profile import Trade, build_volume_profile

UTC = timezone.utc
START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def test_tpo_and_volume_profile_are_distinct():
    bars = pd.DataFrame(
        [
            {"timestamp": START, "available_at": START + timedelta(minutes=30), "open": 100, "high": 101, "low": 100, "close": 100.5, "volume": 10},
            {"timestamp": START + timedelta(minutes=30), "available_at": START + timedelta(minutes=60), "open": 100, "high": 101, "low": 100, "close": 100.5, "volume": 10},
        ]
    )
    tpo = build_tpo_profile(bars, "NQ", tick_size=1.0, bracket_minutes=30)
    volume = build_volume_profile(
        [Trade(100, 10, START, START, "t1"), Trade(102, 100, START, START, "t2")],
        "NQ",
        tick_size=1.0,
    )
    assert tpo.tpo_poc == 100
    assert volume.poc_price == 102
    assert tpo.method == "TPO"


def test_tpo_total_equals_sum_of_occupancy():
    bars = pd.DataFrame(
        [
            {"timestamp": START, "available_at": START + timedelta(minutes=30), "open": 100, "high": 102, "low": 100, "close": 101, "volume": 5},
        ]
    )
    tpo = build_tpo_profile(bars, "NQ", tick_size=1.0, bracket_minutes=30)
    assert tpo.total_tpo == sum(tpo.bins.values())
    assert tpo.total_tpo == 3
