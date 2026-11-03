"""Multi-session research outlook bundle.

Every outlook is research-only: direction probabilities and target-before-stop
probabilities remain null. The bundle supplies session windows, empirical range,
levels, reachability and critical-day context.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from ..backtest.data import ROOT, add_session_column, load_intraday
from ..instruments import InstrumentSpec, get_instrument
from ..macro.calendar import CalendarStore, detect_critical_day, load_sample_calendar
from ..market_clock import ensure_utc, is_trading_day, next_trading_day, session_date
from ..price_levels import build_levels
from ..price_levels.reachability import estimate_touch_probability
from ..regime import classify_regime
from ..research.range_model import expected_range
from ..sessions import SessionSnapshot, session_snapshot, session_window_for
from .v1 import ForecastTarget

FORECAST_DIR = ROOT / "data" / "forecasts"
JOURNAL_PATH = ROOT / "data" / "journal" / "forecast_bundles.jsonl"
SESSION_HORIZONS = {"ASIA": 96, "LONDON": 60, "NEW_YORK": 78}


class SessionOutlook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: Literal["ASIA", "LONDON", "NEW_YORK"]
    session_date: str
    window_start_utc: str
    window_end_utc: str
    as_of: str
    expected_range: dict | None = None
    market_regime: str
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    direction_probability: float | None = None
    consolidation_probability: float | None = None
    targets: list[ForecastTarget] = Field(default_factory=list)
    decision: Literal["LONG", "SHORT", "WAIT", "NO_TRADE"]
    validation_status: Literal["research_only", "validated_shadow", "paper_tested", "live_approved"]
    critical_day: str
    data_provenance: dict


class ForecastBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    instrument: str
    as_of: str
    outlooks: dict[str, SessionOutlook]
    next_day: SessionOutlook | None = None
    critical_day: str
    data_provenance: dict


class BundleJournal:
    def __init__(self, path: Path | None = None):
        self.path = path or JOURNAL_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def all(self) -> list[ForecastBundle]:
        if not self.path.exists():
            return []
        return [
            ForecastBundle.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, bundle: ForecastBundle) -> None:
        if any(item.bundle_id == bundle.bundle_id for item in self.all()):
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(bundle.model_dump_json() + "\n")


def _next_window(spec: InstrumentSpec, session: str, asof: datetime):
    day = session_date(asof, spec)
    for offset in range(0, 10):
        candidate = day + timedelta(days=offset)
        if not is_trading_day(candidate):
            continue
        window = session_window_for(spec, session, candidate)
        if window.start_utc > asof:
            return window
    raise ValueError(f"no future {session} window")


def _consolidation(regime) -> float | None:
    if not regime.future_probabilities:
        return None
    return round(
        sum(
            probability
            for label, probability in regime.future_probabilities.items()
            if label in {"BALANCED", "CHOP", "COMPRESSION", "TRANSITION"}
        ),
        4,
    )


def _outlook(
    window,
    bars,
    spec: InstrumentSpec,
    asof: datetime,
    regime,
    levels,
    critical,
) -> SessionOutlook:
    horizon = SESSION_HORIZONS[window.session]
    try:
        range_forecast = expected_range(bars, horizon_bars=horizon, asof=asof)
        expected = range_forecast.to_dict()
    except ValueError:
        expected = None

    current_price = float(bars[bars["available_at"] <= asof]["close"].iloc[-1])
    candidates = sorted(levels.levels, key=lambda level: abs(level.price - current_price))[:5]
    targets = []
    for level in candidates:
        try:
            touch = estimate_touch_probability(bars, level.price, horizon_bars=horizon, asof=asof)
            probability = touch.probability if np.isfinite(touch.probability) else None
            method = touch.method
            sample_n = touch.sample_n
        except ValueError:
            probability, method, sample_n = None, "UNAVAILABLE", 0
        targets.append(
            ForecastTarget(
                level=level.price,
                zone_low=round(level.zone_low - 2 * spec.tick_size, 4),
                zone_high=round(level.zone_high + 2 * spec.tick_size, 4),
                probability_before_stop=None,
                touch_probability=probability,
                touch_method=method,
                touch_sample_n=sample_n,
                target_horizon="next_session",
                level_type=level.level_type,
            )
        )

    return SessionOutlook(
        session=window.session,
        session_date=window.session_date.isoformat(),
        window_start_utc=window.start_utc.isoformat(),
        window_end_utc=window.end_utc.isoformat(),
        as_of=asof.isoformat(),
        expected_range=expected,
        market_regime=regime.label,
        direction="NEUTRAL",
        direction_probability=None,
        consolidation_probability=_consolidation(regime),
        targets=targets,
        decision="NO_TRADE",
        validation_status="research_only",
        critical_day=critical.state,
        data_provenance={
            "profile_method": levels.metadata.get("profile_method"),
            "level_count": len(levels.levels),
            "regime_reasons": regime.reasons,
            "range_horizon_bars": horizon,
            "range_sample_n": expected.get("sample_n") if expected else None,
            "direction_model": "none",
            "target_probability_model": "none",
        },
    )


def build_bundle_from_bars(
    bars,
    spec: InstrumentSpec,
    asof: datetime,
    calendar: CalendarStore | None = None,
) -> ForecastBundle:
    asof = ensure_utc(asof)
    frame = add_session_column(bars, spec)
    known = frame[frame["available_at"] <= asof]
    if known.empty:
        raise ValueError("no bars available at asof")
    calendar = calendar or load_sample_calendar()
    regime = classify_regime(frame, asof)
    day = session_date(asof, spec)
    levels = build_levels(frame, spec, day, asof)
    critical = detect_critical_day(calendar, asof)

    outlooks = {}
    for session in ("ASIA", "LONDON", "NEW_YORK"):
        window = _next_window(spec, session, asof)
        outlooks[session] = _outlook(window, frame, spec, asof, regime, levels, critical)

    next_day_window = session_window_for(spec, "NEW_YORK", next_trading_day(day))
    next_day = _outlook(next_day_window, frame, spec, asof, regime, levels, critical)

    bundle_id = hashlib.sha1(f"{spec.instrument_id}|{asof.isoformat()}|bundle-v1".encode()).hexdigest()[:16]
    return ForecastBundle(
        bundle_id=bundle_id,
        instrument=spec.instrument_id,
        as_of=asof.isoformat(),
        outlooks=outlooks,
        next_day=next_day,
        critical_day=critical.state,
        data_provenance={
            "bars": "data/market/intraday",
            "calendar_source": critical.data_quality.get("calendar_source"),
            "calendar_point_in_time": critical.data_quality.get("point_in_time"),
            "research_only": True,
        },
    )


def build_forecast_bundle(
    instrument: str = "NQ",
    asof: datetime | None = None,
    journal: bool = True,
) -> ForecastBundle:
    spec = get_instrument(instrument)
    bars, _ = load_intraday(instrument)
    frame = add_session_column(bars, spec)
    asof = ensure_utc(asof) if asof else frame["available_at"].iloc[-1].to_pydatetime()
    bundle = build_bundle_from_bars(frame, spec, asof)
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    (FORECAST_DIR / f"{spec.instrument_id}_bundle.json").write_text(
        json.dumps(bundle.model_dump(), indent=2) + "\n", encoding="utf-8"
    )
    if journal:
        BundleJournal().append(bundle)
    return bundle


__all__ = [
    "ForecastBundle",
    "SessionOutlook",
    "BundleJournal",
    "build_bundle_from_bars",
    "build_forecast_bundle",
]
