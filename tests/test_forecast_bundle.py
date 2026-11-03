from datetime import datetime, timedelta, timezone

import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.forecast.bundle import BundleJournal, build_bundle_from_bars
from nocturne.instruments import get_instrument

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


def test_bundle_is_research_only():
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    bundle = build_bundle_from_bars(frame(), NQ, asof)
    assert set(bundle.outlooks) == {"ASIA", "LONDON", "NEW_YORK"}
    assert bundle.next_day is not None
    for outlook in [*bundle.outlooks.values(), bundle.next_day]:
        assert outlook.decision == "NO_TRADE"
        assert outlook.validation_status == "research_only"
        assert outlook.direction_probability is None
        assert outlook.targets
        assert all(target.probability_before_stop is None for target in outlook.targets)
        assert outlook.expected_range is None  # only one synthetic session, not 20
        assert outlook.consolidation_probability is None
        assert all(target.touch_probability is None for target in outlook.targets)


def test_bundle_journal_is_idempotent(tmp_path):
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    bundle = build_bundle_from_bars(frame(), NQ, asof)
    journal = BundleJournal(tmp_path / "bundles.jsonl")
    journal.append(bundle)
    journal.append(bundle)
    assert len(journal.all()) == 1
