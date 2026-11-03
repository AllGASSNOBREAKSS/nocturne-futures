from datetime import datetime, timezone

from fastapi.testclient import TestClient

from nocturne.api import ForecastService, create_app
from nocturne.contracts import Bias, Decision, Prediction, Quality, Zone
from nocturne.journal import PredictionJournal

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
        market_regime="TREND_DOWN",
        critical_day_state="NORMAL",
        strategy_id="test",
        model_version="v0",
        entry=Zone(lower_price_ticks=100, upper_price_ticks=101),
        stop=Zone(lower_price_ticks=90, upper_price_ticks=91),
        data_quality=Quality(),
        reason_codes=["TEST"],
    )


def client(tmp_path):
    journal_root = tmp_path / "journal"
    journal = PredictionJournal(journal_root)
    journal.append(prediction())
    service = ForecastService(
        journal_root=journal_root,
        registry_root=tmp_path / "registry",
        forecast_root=tmp_path / "forecasts",
    )
    return TestClient(create_app(service))


def test_health_is_read_only(tmp_path):
    response = client(tmp_path).get("/health")
    assert response.status_code == 200
    assert response.json()["read_only"] is True


def test_latest_prediction(tmp_path):
    response = client(tmp_path).get("/v1/predictions/latest?instrument=NQ")
    assert response.status_code == 200
    assert response.json()["prediction_id"] == "p1"


def test_unknown_instrument_404(tmp_path):
    response = client(tmp_path).get("/v1/predictions/latest?instrument=ES")
    assert response.status_code == 404


def test_levels_and_profile_are_explicit_when_absent(tmp_path):
    c = client(tmp_path)
    levels = c.get("/v1/levels?instrument=NQ").json()
    profile = c.get("/v1/auction/profile?instrument=NQ&session=RTH").json()
    assert levels["levels"] == []
    assert levels["reason"] == "NO_LEVEL_ARTIFACT"
    assert profile["profile"] is None
    assert profile["reason"] == "DATA_BLOCKED_OR_NOT_BUILT"


def test_models_status(tmp_path):
    response = client(tmp_path).get("/v1/models/status")
    assert response.status_code == 200
    assert response.json()["models"] == []


def test_market_state(tmp_path):
    response = client(tmp_path).get("/v1/market-state?instrument=NQ")
    assert response.status_code == 200
    assert response.json()["regime"] == "TREND_DOWN"
