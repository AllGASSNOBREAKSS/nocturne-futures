from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.instruments import get_instrument
from nocturne.price_levels import build_levels

UTC = timezone.utc
NQ = get_instrument("NQ")


def bar(ts, close, volume=100):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": close - 0.05,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "volume": volume,
    }


def make_bars(start, count, base):
    return [bar(start + timedelta(minutes=5 * i), base + i * 0.1) for i in range(count)]


def frame():
    prior = pd.DataFrame(make_bars(datetime(2026, 10, 30, 13, 30, tzinfo=UTC), 78, 100))
    overnight = pd.DataFrame(make_bars(datetime(2026, 11, 1, 23, 0, tzinfo=UTC), 100, 101))
    rth = pd.DataFrame(make_bars(datetime(2026, 11, 2, 14, 30, tzinfo=UTC), 78, 102))
    return add_session_column(pd.concat([prior, overnight, rth], ignore_index=True), NQ)


def test_levels_include_structural_sources():
    levels = build_levels(frame(), NQ, date(2026, 11, 2), datetime(2026, 11, 2, 16, 0, tzinfo=UTC))
    types = {level.level_type for level in levels.levels}
    sources = {source for level in levels.levels for source in level.sources}
    assert "PRIOR_HIGH" in types or "CONFLUENCE" in types
    assert "OVERNIGHT_HIGH" in types or "CONFLUENCE" in types
    assert "volume_profile" in sources
    assert "vwap" in sources
    assert all(level.zone_low <= level.price <= level.zone_high for level in levels.levels)


def test_levels_do_not_use_future_bars():
    bars = frame()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    first = build_levels(bars, NQ, date(2026, 11, 2), asof)
    future = pd.DataFrame(make_bars(datetime(2026, 11, 2, 17, 0, tzinfo=UTC), 20, 200))
    future = add_session_column(future, NQ)
    extended = pd.concat([bars, future], ignore_index=True)
    second = build_levels(extended, NQ, date(2026, 11, 2), asof)
    assert [(l.level_type, l.price) for l in first.levels] == [
        (l.level_type, l.price) for l in second.levels
    ]


def test_level_set_serializes():
    levels = build_levels(frame(), NQ, date(2026, 11, 2), datetime(2026, 11, 2, 16, 0, tzinfo=UTC))
    payload = levels.to_dict()
    assert payload["instrument_id"] == "NQ"
    assert isinstance(payload["levels"], list)
    assert payload["metadata"]["profile_method"] == "BAR_APPROXIMATION"
