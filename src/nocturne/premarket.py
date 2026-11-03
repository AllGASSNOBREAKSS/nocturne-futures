"""Machine-readable premarket state.

Built from RTH and overnight bars. If intraday bars are absent, the state is
explicitly marked missing rather than filled with a guess.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime

import pandas as pd

from .auction.session import session_bars
from .instruments import InstrumentSpec
from .market_clock import next_trading_day, session_window, to_et


@dataclass
class PremarketState:
    session_date: str
    asof: str
    nq_gap: float | None = None
    nq_overnight_high: float | None = None
    nq_overnight_low: float | None = None
    nq_prior_rth_high: float | None = None
    nq_prior_rth_low: float | None = None
    nq_prior_rth_close: float | None = None
    es_gap: float | None = None
    es_overnight_high: float | None = None
    es_overnight_low: float | None = None
    es_prior_rth_high: float | None = None
    es_prior_rth_low: float | None = None
    es_prior_rth_close: float | None = None
    leadership: str = "UNKNOWN"
    vix_state: str = "UNKNOWN"
    events: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    data_quality: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _prior_trading_day(day: date) -> date:
    from .market_clock import is_trading_day

    prior = day
    while True:
        prior = prior.fromordinal(prior.toordinal() - 1)
        if is_trading_day(prior):
            return prior


def _session_stats(
    bars: pd.DataFrame, spec: InstrumentSpec, session: str, day: date
) -> dict | None:
    frame = session_bars(bars, spec, session, day)
    if frame.empty:
        return None
    return {
        "high": float(frame["high"].max()),
        "low": float(frame["low"].min()),
        "close": float(frame["close"].iloc[-1]),
        "last_time": frame["timestamp"].iloc[-1],
    }


def build_premarket_state(
    nq_bars: pd.DataFrame,
    es_bars: pd.DataFrame,
    nq_spec: InstrumentSpec,
    es_spec: InstrumentSpec,
    session_date: date,
    asof: datetime,
    vix_level: float | None = None,
    events: list[dict] | None = None,
) -> PremarketState:
    prior = _prior_trading_day(session_date)
    flags: list[str] = ["OVERNIGHT_PROVISIONAL"]
    quality = {"missing": False, "coverage": 1.0}

    def instrument_state(bars: pd.DataFrame, spec: InstrumentSpec) -> dict:
        overnight = _session_stats(bars, spec, "OVERNIGHT", session_date)
        rth = _session_stats(bars, spec, "RTH", prior)
        if overnight is None or rth is None:
            return {"gap": None, "overnight": overnight, "rth": rth}
        gap = overnight["close"] / rth["close"] - 1.0
        return {"gap": gap, "overnight": overnight, "rth": rth}

    nq = instrument_state(nq_bars, nq_spec)
    es = instrument_state(es_bars, es_spec)
    if nq["gap"] is None or es["gap"] is None:
        quality = {"missing": True, "coverage": 0.0}
        flags.append("INTRADAY_BARS_MISSING")

    leadership = "UNKNOWN"
    if nq["gap"] is not None and es["gap"] is not None:
        diff = nq["gap"] - es["gap"]
        leadership = "NQ_LED" if diff > 0.001 else "ES_LED" if diff < -0.001 else "MIXED"

    vix_state = "UNKNOWN"
    if vix_level is not None:
        vix_state = "STRESS" if vix_level >= 25 else "ELEVATED" if vix_level >= 20 else "NORMAL"

    if events is None:
        events = []
        flags.append("CALENDAR_NOT_CONFIGURED")

    return PremarketState(
        session_date=session_date.isoformat(),
        asof=asof.isoformat(),
        nq_gap=round(nq["gap"], 6) if nq["gap"] is not None else None,
        nq_overnight_high=nq["overnight"]["high"] if nq["overnight"] else None,
        nq_overnight_low=nq["overnight"]["low"] if nq["overnight"] else None,
        nq_prior_rth_high=nq["rth"]["high"] if nq["rth"] else None,
        nq_prior_rth_low=nq["rth"]["low"] if nq["rth"] else None,
        nq_prior_rth_close=nq["rth"]["close"] if nq["rth"] else None,
        es_gap=round(es["gap"], 6) if es["gap"] is not None else None,
        es_overnight_high=es["overnight"]["high"] if es["overnight"] else None,
        es_overnight_low=es["overnight"]["low"] if es["overnight"] else None,
        es_prior_rth_high=es["rth"]["high"] if es["rth"] else None,
        es_prior_rth_low=es["rth"]["low"] if es["rth"] else None,
        es_prior_rth_close=es["rth"]["close"] if es["rth"] else None,
        leadership=leadership,
        vix_state=vix_state,
        events=events,
        flags=flags,
        data_quality=quality,
    )
