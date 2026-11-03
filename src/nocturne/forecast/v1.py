"""Structured Forecast V1.

This is a research-only contract. It does not fabricate direction or target
probabilities: when no validated model exists, the probability fields are null
and the decision is NO_TRADE.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from ..backtest.data import ROOT, add_session_column, load_intraday
from ..instruments import InstrumentSpec, get_instrument
from ..macro.calendar import CalendarStore, detect_critical_day, load_sample_calendar
from ..market_clock import ensure_utc, session_date
from ..price_levels import build_levels
from ..price_levels.reachability import estimate_touch_probability
from ..regime import classify_regime
from ..research.range_model import expected_range

JOURNAL_PATH = ROOT / "data" / "journal" / "forecasts_v1.jsonl"
FORECAST_DIR = ROOT / "data" / "forecasts"


class ForecastTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: float
    zone_low: float
    zone_high: float
    probability_before_stop: float | None = None
    touch_probability: float | None = None
    touch_method: str | None = None
    touch_sample_n: int | None = None
    target_horizon: str
    level_type: str


class ForecastV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_id: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    contract: str | None = None
    as_of: str
    forecast_horizon: str
    market_regime: str
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    direction_probability: float | None = None
    expected_range: dict | None = None
    consolidation_probability: float | None = None
    candidate_entry_zone: dict | None = None
    stop_loss: float | None = None
    targets: list[ForecastTarget] = Field(default_factory=list)
    critical_day: str
    macro_warnings: list[str] = Field(default_factory=list)
    expected_value_after_costs: float | None = None
    model_version: str
    validation_status: Literal["research_only", "validated_shadow", "paper_tested", "live_approved"]
    decision: Literal["LONG", "SHORT", "WAIT", "NO_TRADE"]
    data_provenance: dict
    strategy_id: str | None = None
    signal_id: str | None = None
    calibration_version: str | None = None


class ForecastJournal:
    def __init__(self, path: Path | None = None):
        self.path = path or JOURNAL_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _all(self) -> list[ForecastV1]:
        if not self.path.exists():
            return []
        return [
            ForecastV1.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, forecast: ForecastV1) -> None:
        if any(item.forecast_id == forecast.forecast_id for item in self._all()):
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(forecast.model_dump_json() + "\n")

    def latest(self, instrument: str) -> ForecastV1 | None:
        matches = [item for item in self._all() if item.instrument == instrument.upper()]
        return matches[-1] if matches else None


def _nearest(levels, price: float):
    return min(levels, key=lambda level: abs(level.price - price)) if levels else None


def build_forecast_from_bars(
    bars,
    spec: InstrumentSpec,
    asof: datetime,
    contract: str | None = None,
    calendar: CalendarStore | None = None,
) -> ForecastV1:
    asof = ensure_utc(asof)
    frame = add_session_column(bars, spec)
    day = session_date(asof, spec)
    known = frame[frame["available_at"] <= asof]
    if known.empty:
        raise ValueError("no bars available at asof")
    current_price = float(known["close"].iloc[-1])

    level_set = build_levels(frame, spec, day, asof)
    regime = classify_regime(frame, asof)
    range_forecast = expected_range(frame, horizon_bars=78, asof=asof)
    calendar = calendar or load_sample_calendar()
    critical = detect_critical_day(calendar, asof)

    if regime.label == "TREND_UP":
        direction = "BULLISH"
    elif regime.label == "TREND_DOWN":
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    if direction == "BULLISH":
        candidates = sorted(
            [level for level in level_set.levels if level.price > current_price],
            key=lambda level: level.price,
        )
        stop = current_price - range_forecast.atr
    elif direction == "BEARISH":
        candidates = sorted(
            [level for level in level_set.levels if level.price < current_price],
            key=lambda level: level.price,
            reverse=True,
        )
        stop = current_price + range_forecast.atr
    else:
        candidates = sorted(level_set.levels, key=lambda level: abs(level.price - current_price))
        stop = None

    targets = []
    for level in candidates[:3]:
        touch = estimate_touch_probability(frame, level.price, horizon_bars=78, asof=asof)
        targets.append(
            ForecastTarget(
                level=level.price,
                zone_low=round(level.zone_low - 2 * spec.tick_size, 4),
                zone_high=round(level.zone_high + 2 * spec.tick_size, 4),
                probability_before_stop=None,
                touch_probability=(
                    touch.probability if np.isfinite(touch.probability) else None
                ),
                touch_method=touch.method,
                touch_sample_n=touch.sample_n,
                target_horizon="session",
                level_type=level.level_type,
            )
        )
    nearest = _nearest(level_set.levels, current_price)
    entry_zone = (
        {
            "low": round(nearest.zone_low - 2 * spec.tick_size, 4),
            "high": round(nearest.zone_high + 2 * spec.tick_size, 4),
            "level_type": nearest.level_type,
            "level_id": nearest.level_id,
        }
        if nearest
        else None
    )

    consolidation = None
    if regime.future_probabilities:
        consolidation = round(
            sum(
                probability
                for label, probability in regime.future_probabilities.items()
                if label in {"BALANCED", "CHOP", "COMPRESSION", "TRANSITION"}
            ),
            4,
        )

    forecast_id = hashlib.sha1(
        f"{spec.instrument_id}|{asof.isoformat()}|v1".encode()
    ).hexdigest()[:16]
    return ForecastV1(
        forecast_id=forecast_id,
        instrument=spec.instrument_id,
        contract=contract,
        as_of=asof.isoformat(),
        forecast_horizon="new_york_session",
        market_regime=regime.label,
        direction=direction,
        direction_probability=None,
        expected_range=range_forecast.to_dict(),
        consolidation_probability=consolidation,
        candidate_entry_zone=entry_zone,
        stop_loss=round(stop, 4) if stop is not None else None,
        targets=targets,
        critical_day=critical.state,
        macro_warnings=["CALENDAR_SAMPLE_ONLY", "VX_FUTURES_UNAVAILABLE", *critical.reasons],
        expected_value_after_costs=None,
        model_version="none",
        validation_status="research_only",
        decision="NO_TRADE",
        data_provenance={
            "bars": "data/market/intraday",
            "profile_method": level_set.metadata.get("profile_method"),
            "level_count": len(level_set.levels),
            "regime_reasons": regime.reasons,
            "range_sample_n": range_forecast.sample_n,
            "range_bucket": range_forecast.bucket,
            "calendar_source": critical.data_quality.get("calendar_source"),
            "calendar_event_count": critical.data_quality.get("event_count"),
            "calendar_point_in_time": critical.data_quality.get("point_in_time"),
        },
        strategy_id=None,
        signal_id=None,
        calibration_version=None,
    )


def build_forecast_v1(
    instrument: str = "NQ",
    asof: datetime | None = None,
    contract: str | None = None,
    journal: bool = True,
) -> ForecastV1:
    spec = get_instrument(instrument)
    bars, _ = load_intraday(instrument)
    frame = add_session_column(bars, spec)
    asof = ensure_utc(asof) if asof else frame["available_at"].iloc[-1].to_pydatetime()
    forecast = build_forecast_from_bars(frame, spec, asof, contract)
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    (FORECAST_DIR / f"{spec.instrument_id}_v1.json").write_text(
        json.dumps(forecast.model_dump(), indent=2) + "\n", encoding="utf-8"
    )
    if journal:
        ForecastJournal().append(forecast)
    return forecast
