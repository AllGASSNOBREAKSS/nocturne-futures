from datetime import datetime, timedelta, timezone

import pytest

from nocturne.auction.volume_profile import (
    Trade,
    build_bar_approximation,
    build_volume_profile,
    composite_profile,
)

UTC = timezone.utc
BASE = datetime(2026, 11, 2, 15, 0, tzinfo=UTC)


def trade(price: float, qty: float, minutes: int = 0, available_offset: int = 0) -> Trade:
    return Trade(
        price=price,
        qty=qty,
        event_time=BASE + timedelta(minutes=minutes),
        available_at=BASE + timedelta(minutes=minutes + available_offset),
        trade_id=f"{price}-{minutes}",
    )


def test_poc_and_value_area_golden_fixture():
    trades = [
        trade(100, 10, 0),
        trade(101, 20, 1),
        trade(102, 50, 2),
        trade(103, 15, 3),
        trade(104, 5, 4),
    ]
    profile = build_volume_profile(trades, "NQ", tick_size=1.0, value_area_share=0.70)
    assert profile.total_volume == 100
    assert profile.poc_price == 102
    assert profile.val_price == 101
    assert profile.vah_price == 102
    assert profile.value_area_volume == pytest.approx(70)


def test_volume_conservation():
    trades = [trade(100 + i, 10 + i, i) for i in range(5)]
    profile = build_volume_profile(trades, "NQ", tick_size=1.0)
    assert sum(profile.bins.values()) == pytest.approx(profile.total_volume)


def test_poc_tie_breaks_nearest_vwap_then_lower():
    trades = [trade(100, 50, 0), trade(102, 50, 1)]
    profile = build_volume_profile(trades, "NQ", tick_size=1.0)
    # VWAP is 101, equidistant; lower bin wins.
    assert profile.poc_price == 100


def test_developing_profile_excludes_unavailable_trades():
    trades = [
        trade(100, 50, 0, available_offset=0),
        trade(110, 100, 1, available_offset=60),
    ]
    asof = BASE + timedelta(minutes=10)
    profile = build_volume_profile(trades, "NQ", tick_size=1.0, asof=asof)
    assert profile.poc_price == 100
    assert profile.total_volume == 50


def test_bar_approximation_is_labelled_and_conserves_volume():
    import pandas as pd

    bars = pd.DataFrame(
        [
            {
                "timestamp": BASE,
                "available_at": BASE + timedelta(minutes=5),
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 300,
            }
        ]
    )
    profile = build_bar_approximation(bars, "NQ", tick_size=1.0)
    assert profile.method == "BAR_APPROXIMATION"
    assert profile.quality == "APPROXIMATION"
    assert sum(profile.bins.values()) == pytest.approx(300)


def test_composite_profile_sums_bins():
    a = build_volume_profile([trade(100, 10)], "NQ", tick_size=1.0)
    b = build_volume_profile([trade(101, 20)], "NQ", tick_size=1.0)
    composite = composite_profile([a, b], "NQ")
    assert composite.total_volume == 30
    assert sum(composite.bins.values()) == pytest.approx(30)


def test_empty_profile_raises():
    with pytest.raises(ValueError):
        build_volume_profile([], "NQ", tick_size=1.0)
