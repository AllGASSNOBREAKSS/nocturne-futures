from datetime import datetime, timedelta, timezone

import pytest

from nocturne.contracts import Bias, Decision, Prediction, Quality, Zone
from nocturne.journal import Outcome, PredictionJournal

UTC = timezone.utc


def prediction(prediction_id="p1", instrument="NQ"):
    now = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)
    return Prediction(
        prediction_id=prediction_id,
        instrument_id=instrument,
        asof_utc=now,
        data_watermark_utc=now,
        horizon_seconds=3600,
        bias=Bias.NEUTRAL,
        decision=Decision.NO_TRADE,
        market_regime="UNKNOWN",
        critical_day_state="NORMAL",
        strategy_id="test",
        model_version="v0",
        entry=Zone(lower_price_ticks=100, upper_price_ticks=101),
        stop=Zone(lower_price_ticks=90, upper_price_ticks=91),
        data_quality=Quality(),
        reason_codes=["TEST"],
    )


def test_append_get_latest(tmp_path):
    journal = PredictionJournal(tmp_path)
    journal.append(prediction("p1"))
    journal.append(prediction("p2"))
    assert journal.get("p1").prediction_id == "p1"
    assert journal.latest("NQ").prediction_id == "p2"
    assert journal.latest("ES") is None


def test_duplicate_prediction_rejected(tmp_path):
    journal = PredictionJournal(tmp_path)
    journal.append(prediction("p1"))
    with pytest.raises(ValueError):
        journal.append(prediction("p1"))


def test_resolve_outcome(tmp_path):
    journal = PredictionJournal(tmp_path)
    journal.append(prediction("p1"))
    journal.resolve(
        Outcome(
            prediction_id="p1",
            resolved_at=datetime(2026, 11, 4, 21, 0, tzinfo=UTC),
            outcome="TP1",
            exit_price=105.0,
            points=5.0,
        )
    )
    assert len(journal.outcomes()) == 1
    with pytest.raises(ValueError):
        journal.resolve(
            Outcome(
                prediction_id="p1",
                resolved_at=datetime(2026, 11, 4, 21, 0, tzinfo=UTC),
                outcome="STOP",
            )
        )
