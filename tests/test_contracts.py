from datetime import date, datetime, timezone

import pytest

from nocturne.contracts import (
    Bias,
    Decision,
    EventType,
    MarketEvent,
    Prediction,
    Quality,
    Zone,
)


def event(**overrides):
    base = dict(
        event_id="e1",
        source="test",
        instrument_id="NQ",
        event_type=EventType.BAR,
        event_time_utc=datetime(2026, 11, 3, 14, 30, tzinfo=timezone.utc),
        available_at_utc=datetime(2026, 11, 3, 14, 35, tzinfo=timezone.utc),
        received_at_utc=datetime(2026, 11, 3, 14, 35, 1, tzinfo=timezone.utc),
        payload={"close": 100.0},
    )
    base.update(overrides)
    return MarketEvent(**base)


def test_event_accepts_valid_envelope():
    ev = event()
    assert ev.instrument_id == "NQ"
    assert ev.quality.coverage == 1.0


def test_event_rejects_available_before_event():
    with pytest.raises(ValueError):
        event(available_at_utc=datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc))


def test_event_rejects_received_before_available():
    with pytest.raises(ValueError):
        event(received_at_utc=datetime(2026, 11, 3, 14, 30, tzinfo=timezone.utc))


def test_zone_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        Zone(lower_price_ticks=10, upper_price_ticks=5)


def test_prediction_no_trade_cannot_claim_positive_ev():
    with pytest.raises(ValueError):
        Prediction(
            prediction_id="p1",
            instrument_id="NQ",
            asof_utc=datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc),
            data_watermark_utc=datetime(2026, 11, 3, 13, 55, tzinfo=timezone.utc),
            horizon_seconds=3600,
            bias=Bias.NEUTRAL,
            decision=Decision.NO_TRADE,
            market_regime="UNKNOWN",
            critical_day_state="NORMAL",
            strategy_id="none",
            model_version="v0",
            entry=Zone(lower_price_ticks=100, upper_price_ticks=101),
            stop=Zone(lower_price_ticks=90, upper_price_ticks=91),
            expected_net_value_points=5.0,
            data_quality=Quality(),
        )


def test_prediction_long_requires_target():
    with pytest.raises(ValueError):
        Prediction(
            prediction_id="p1",
            instrument_id="NQ",
            asof_utc=datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc),
            data_watermark_utc=datetime(2026, 11, 3, 13, 55, tzinfo=timezone.utc),
            horizon_seconds=3600,
            bias=Bias.BULLISH,
            decision=Decision.LONG,
            market_regime="TREND",
            critical_day_state="NORMAL",
            strategy_id="orb",
            model_version="v0",
            entry=Zone(lower_price_ticks=100, upper_price_ticks=101),
            stop=Zone(lower_price_ticks=90, upper_price_ticks=91),
            data_quality=Quality(),
        )
