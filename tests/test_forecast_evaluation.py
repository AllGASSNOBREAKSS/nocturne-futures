from datetime import datetime, timedelta, timezone

import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.forecast.bundle import build_bundle_from_bars
from nocturne.forecast.evaluation import evaluate_bundle, evaluate_forecast
from nocturne.forecast.v1 import build_forecast_from_bars
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


def test_forecast_evaluation_uses_only_future_bars():
    bars = frame()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    forecast = build_forecast_from_bars(bars, NQ, asof)
    evaluation = evaluate_forecast(forecast, bars, horizon_bars=12)
    assert evaluation.status == "EVALUATED"
    assert evaluation.realized_range is not None and evaluation.realized_range > 0
    assert evaluation.p50_covered is not None
    assert len(evaluation.target_touches) == len(forecast.targets)
    assert evaluation.direction_outcome == "UNVALIDATED_DIRECTION"


def test_partial_horizon_is_not_scored():
    bars = frame()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    forecast = build_forecast_from_bars(bars, NQ, asof)
    result = evaluate_forecast(forecast, bars, horizon_bars=78)
    assert result.status == "NOT_MATURED"
    assert result.realized_range is None


def test_unmatured_bundle_is_explicit():
    bars = frame()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    bundle = build_bundle_from_bars(bars, NQ, asof)
    result = evaluate_bundle(bundle, bars)
    assert result["outcomes"]
    assert all(item["status"] == "NOT_MATURED" for item in result["outcomes"].values())
