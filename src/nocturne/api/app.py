"""Read-only FastAPI application. No order endpoints exist."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from ..contracts import Prediction
from .service import ForecastService


def create_app(service: ForecastService | None = None) -> FastAPI:
    service = service or ForecastService()
    app = FastAPI(
        title="Nocturne Futures API",
        version="2.0.0",
        description="Read-only research API. No broker order placement.",
    )

    @app.get("/health")
    def health() -> dict:
        return service.health()

    @app.get("/v1/predictions/latest", response_model=Prediction)
    def latest_prediction(instrument: str = Query(..., min_length=1)) -> Prediction:
        prediction = service.latest(instrument)
        if prediction is None:
            raise HTTPException(status_code=404, detail="no prediction for instrument")
        return prediction

    @app.get("/v1/predictions/{prediction_id}", response_model=Prediction)
    def prediction(prediction_id: str) -> Prediction:
        result = service.prediction(prediction_id)
        if result is None:
            raise HTTPException(status_code=404, detail="prediction not found")
        return result

    @app.get("/v1/levels")
    def levels(instrument: str = Query(..., min_length=1)) -> dict:
        return service.levels(instrument)

    @app.get("/v1/auction/profile")
    def auction_profile(
        instrument: str = Query(..., min_length=1),
        session: str = Query("RTH"),
    ) -> dict:
        return service.auction_profile(instrument, session)

    @app.get("/v1/intermarket/state")
    def intermarket_state() -> dict:
        return service.intermarket_state()

    @app.get("/v1/premarket/state")
    def premarket_state() -> dict:
        return service.premarket_state()

    @app.get("/v1/forecast/v1")
    def forecast_v1(instrument: str = Query(..., min_length=1)) -> dict:
        return service.forecast_v1(instrument)

    @app.get("/v1/events/upcoming")
    def events_upcoming() -> dict:
        return service.events_upcoming()

    @app.get("/v1/models/status")
    def models_status() -> dict:
        return service.models_status()

    @app.get("/v1/market-state")
    def market_state(instrument: str = Query(..., min_length=1)) -> dict:
        prediction = service.latest(instrument)
        if prediction is None:
            return {"instrument": instrument.upper(), "state": None, "reason": "NO_PREDICTION"}
        return {
            "instrument": prediction.instrument_id,
            "asof_utc": prediction.asof_utc,
            "regime": prediction.market_regime,
            "critical_day_state": prediction.critical_day_state,
            "data_quality": prediction.data_quality.model_dump(),
        }

    return app


app = create_app()
