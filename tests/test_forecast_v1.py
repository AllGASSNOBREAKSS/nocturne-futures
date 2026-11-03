from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.forecast import ForecastJournal, build_forecast_from_bars
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


def test_forecast_contract_is_honest():
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    forecast = build_forecast_from_bars(frame(), NQ, asof)
    assert forecast.decision == "NO_TRADE"
    assert forecast.validation_status == "research_only"
    assert forecast.direction_probability is None
    assert forecast.expected_value_after_costs is None
    assert forecast.targets
    assert all(target.probability_before_stop is None for target in forecast.targets)
    assert forecast.expected_range["p50"] <= forecast.expected_range["p80"]
    assert forecast.data_provenance["profile_method"] == "BAR_APPROXIMATION"


def test_forecast_journal_is_idempotent(tmp_path):
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    forecast = build_forecast_from_bars(frame(), NQ, asof)
    journal = ForecastJournal(tmp_path / "forecasts.jsonl")
    journal.append(forecast)
    journal.append(forecast)
    assert len(journal._all()) == 1
    assert journal.latest("NQ").forecast_id == forecast.forecast_id
