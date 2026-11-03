"""Outcome evaluation for matured Forecast V1 and session bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .bundle import ForecastBundle
from .v1 import ForecastV1


@dataclass
class ForecastEvaluation:
    forecast_id: str
    instrument: str
    asof: str
    status: str
    horizon_bars: int
    realized_high: float | None = None
    realized_low: float | None = None
    realized_range: float | None = None
    p50_covered: bool | None = None
    p80_covered: bool | None = None
    p90_covered: bool | None = None
    direction_outcome: str = "UNVALIDATED_DIRECTION"
    target_touches: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _prepared(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    return frame.sort_values("timestamp").reset_index(drop=True)


def evaluate_forecast(
    forecast: ForecastV1,
    bars: pd.DataFrame,
    horizon_bars: int = 78,
) -> ForecastEvaluation:
    frame = _prepared(bars)
    asof = pd.Timestamp(forecast.as_of)
    if asof.tzinfo is None:
        asof = asof.tz_localize("UTC")
    future = frame[frame["available_at"] > asof].head(horizon_bars)
    if future.empty:
        return ForecastEvaluation(
            forecast_id=forecast.forecast_id,
            instrument=forecast.instrument,
            asof=forecast.as_of,
            status="NOT_MATURED",
            horizon_bars=horizon_bars,
            notes=["no bars after as_of"],
        )
    high = float(future["high"].max())
    low = float(future["low"].min())
    realized = high - low
    expected = forecast.expected_range or {}
    p50 = expected.get("p50")
    p80 = expected.get("p80")
    p90 = expected.get("p90")
    current = frame[frame["available_at"] <= asof]
    current_close = float(current["close"].iloc[-1]) if not current.empty else None
    future_close = float(future["close"].iloc[-1])
    outcome = "UNVALIDATED_DIRECTION"
    if forecast.direction_probability is not None and current_close is not None:
        if forecast.direction == "BULLISH":
            outcome = "CORRECT" if future_close > current_close else "INCORRECT"
        elif forecast.direction == "BEARISH":
            outcome = "CORRECT" if future_close < current_close else "INCORRECT"
        else:
            atr = expected.get("atr")
            outcome = (
                "CORRECT"
                if atr and abs(future_close - current_close) <= 0.5 * atr
                else "INCORRECT"
            )
    touches = []
    for target in forecast.targets:
        if current_close is None:
            touched = None
        elif target.level > current_close:
            touched = high >= target.level
        else:
            touched = low <= target.level
        touches.append(
            {
                "level": target.level,
                "level_type": target.level_type,
                "touch_probability": target.touch_probability,
                "touched": touched,
            }
        )
    return ForecastEvaluation(
        forecast_id=forecast.forecast_id,
        instrument=forecast.instrument,
        asof=forecast.as_of,
        status="EVALUATED",
        horizon_bars=horizon_bars,
        realized_high=round(high, 4),
        realized_low=round(low, 4),
        realized_range=round(realized, 4),
        p50_covered=(realized <= p50) if p50 is not None else None,
        p80_covered=(realized <= p80) if p80 is not None else None,
        p90_covered=(realized <= p90) if p90 is not None else None,
        direction_outcome=outcome,
        target_touches=touches,
    )


def evaluate_bundle(bundle: ForecastBundle, bars: pd.DataFrame) -> dict:
    frame = _prepared(bars)
    asof = pd.Timestamp(bundle.as_of)
    if asof.tzinfo is None:
        asof = asof.tz_localize("UTC")
    results = {}
    for name, outlook in {**bundle.outlooks, "NEXT_DAY": bundle.next_day}.items():
        if outlook is None:
            continue
        start = pd.Timestamp(outlook.window_start_utc)
        end = pd.Timestamp(outlook.window_end_utc)
        window = frame[
            (frame["available_at"] > asof)
            & (frame["timestamp"] >= start)
            & (frame["timestamp"] < end)
        ]
        if window.empty:
            results[name] = {
                "status": "NOT_MATURED",
                "session_date": outlook.session_date,
                "window_start_utc": outlook.window_start_utc,
                "window_end_utc": outlook.window_end_utc,
            }
            continue
        high = float(window["high"].max())
        low = float(window["low"].min())
        realized = high - low
        expected = outlook.expected_range or {}
        current = frame[frame["available_at"] <= asof]
        current_close = float(current["close"].iloc[-1]) if not current.empty else None
        touches = []
        for target in outlook.targets:
            if current_close is None:
                touched = None
            elif target.level > current_close:
                touched = high >= target.level
            else:
                touched = low <= target.level
            touches.append(
                {
                    "level": target.level,
                    "touch_probability": target.touch_probability,
                    "touched": touched,
                }
            )
        results[name] = {
            "status": "EVALUATED",
            "session_date": outlook.session_date,
            "realized_high": round(high, 4),
            "realized_low": round(low, 4),
            "realized_range": round(realized, 4),
            "p50_covered": (realized <= expected.get("p50")) if expected.get("p50") is not None else None,
            "p80_covered": (realized <= expected.get("p80")) if expected.get("p80") is not None else None,
            "p90_covered": (realized <= expected.get("p90")) if expected.get("p90") is not None else None,
            "target_touches": touches,
            "direction_outcome": "UNVALIDATED_DIRECTION",
        }
    return {"bundle_id": bundle.bundle_id, "as_of": bundle.as_of, "outcomes": results}


__all__ = ["ForecastEvaluation", "evaluate_forecast", "evaluate_bundle"]
