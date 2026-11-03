"""Analytical session windows and point-in-time session snapshots.

ASIA, LONDON, PREMARKET and NEW_YORK are **analytical time windows** in
America/New_York, not official exchange sessions. RTH, OVERNIGHT and ETH use the
exchange calendar. Early-close dates are explicit and testable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from .auction.session import window_range
from .auction.volume_profile import build_bar_approximation
from .instruments import InstrumentSpec
from .market_clock import (
    ET,
    UTC,
    SessionWindow,
    ensure_utc,
    is_trading_day,
    session_window,
    to_et,
)

ANALYTICAL_WINDOWS: dict[str, tuple[time, time]] = {
    "ASIA": (time(19, 0), time(3, 0)),
    "LONDON": (time(3, 0), time(8, 0)),
    "PREMARKET": (time(8, 0), time(9, 30)),
    "NEW_YORK": (time(9, 30), time(16, 0)),
}

# CME equity-index early closes: day after Thanksgiving and Christmas Eve when
# the exchange is open. These are calendar dates, not recurring rules.
EARLY_CLOSE_DATES: set[date] = {
    date(2025, 11, 28),
    date(2025, 12, 24),
    date(2026, 11, 27),
    date(2026, 12, 24),
    date(2027, 11, 26),
    date(2027, 12, 23),
}


def _at(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=ET).astimezone(UTC)


def session_window_for(spec: InstrumentSpec, session: str, day: date) -> SessionWindow:
    name = session.upper()
    if name in {"OVERNIGHT", "ETH"}:
        return session_window(spec, name, day)
    if name == "RTH":
        base = session_window(spec, "RTH", day)
        end = _at(day, time(13, 0)) if day in EARLY_CLOSE_DATES else base.end_utc
        return SessionWindow(name, day, base.start_utc, end)
    if name == "NEW_YORK":
        start = _at(day, time(9, 30))
        end = _at(day, time(13, 0)) if day in EARLY_CLOSE_DATES else _at(day, time(16, 0))
        return SessionWindow(name, day, start, end)
    if name not in ANALYTICAL_WINDOWS:
        raise ValueError(f"unknown session {session!r}")
    start_clock, end_clock = ANALYTICAL_WINDOWS[name]
    start = datetime.combine(day, start_clock, tzinfo=ET)
    end = datetime.combine(day, end_clock, tzinfo=ET)
    if end <= start:
        start -= timedelta(days=1)
    return SessionWindow(name, day, start.astimezone(UTC), end.astimezone(UTC))


def _atr(frame: pd.DataFrame, window: int = 14) -> float:
    if len(frame) < 2:
        return float("nan")
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    value = tr.rolling(window).mean().iloc[-1]
    return float(value) if np.isfinite(value) else float("nan")


@dataclass(frozen=True)
class SessionSnapshot:
    instrument_id: str
    session: str
    session_date: str
    start_utc: str
    end_utc: str
    asof: str
    complete: bool
    bars: int
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    vwap: float | None
    range_points: float | None
    return_pct: float | None
    atr: float | None
    range_atr: float | None
    efficiency: float | None
    volatility: float | None
    gap_pct: float | None
    prior_high: float | None
    prior_low: float | None
    prior_close: float | None
    ib_high: float | None
    ib_low: float | None
    poc: float | None
    vah: float | None
    val: float | None
    profile_method: str
    compression: bool
    data_quality: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _prior_session_day(spec: InstrumentSpec, day: date) -> date:
    cur = day - timedelta(days=1)
    while not is_trading_day(cur):
        cur -= timedelta(days=1)
    return cur


def _prior_rth(bars: pd.DataFrame, spec: InstrumentSpec, day: date) -> pd.DataFrame:
    prior = _prior_session_day(spec, day)
    window = session_window(spec, "RTH", prior)
    return bars[(bars["timestamp"] >= window.start_utc) & (bars["timestamp"] < window.end_utc)]


def session_snapshot(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    day: date,
    session: str,
    asof: datetime | None = None,
) -> SessionSnapshot | None:
    window = session_window_for(spec, session, day)
    asof = ensure_utc(asof) if asof is not None else window.end_utc
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    known = frame[frame["available_at"] <= asof]
    current = known[
        (known["timestamp"] >= window.start_utc) & (known["timestamp"] < window.end_utc)
    ].sort_values("timestamp")
    if current.empty:
        return None

    close = float(current["close"].iloc[-1])
    open_price = float(current["open"].iloc[0])
    high = float(current["high"].max())
    low = float(current["low"].min())
    volume = float(current["volume"].sum())
    atr = _atr(known)
    range_points = high - low
    returns = np.log(current["close"] / current["close"].shift(1)).dropna()
    efficiency = (
        abs(close - open_price) / float(current["close"].diff().abs().sum())
        if current["close"].diff().abs().sum() > 0
        else 0.0
    )
    vwap = None
    if volume > 0:
        typical = (current["high"] + current["low"] + current["close"]) / 3.0
        vwap = float((typical * current["volume"]).sum() / volume)

    prior = _prior_rth(known, spec, day)
    prior_high = float(prior["high"].max()) if not prior.empty else None
    prior_low = float(prior["low"].min()) if not prior.empty else None
    prior_close = float(prior["close"].iloc[-1]) if not prior.empty else None
    gap_pct = (open_price / prior_close - 1.0) if prior_close else None

    ib_high = ib_low = None
    if session.upper() in {"RTH", "NEW_YORK"}:
        ib_end = window.start_utc + timedelta(minutes=60)
        if asof >= ib_end:
            try:
                ib = window_range(known, window.start_utc, ib_end, asof)
                ib_high, ib_low = ib.high, ib.low
            except ValueError:
                pass

    poc = vah = val = None
    profile_method = "UNAVAILABLE"
    if len(current) >= 2:
        try:
            profile = build_bar_approximation(current, spec.instrument_id, spec.tick_size, asof=asof)
            poc, vah, val = profile.poc_price, profile.vah_price, profile.val_price
            profile_method = profile.method
        except ValueError:
            pass

    return SessionSnapshot(
        instrument_id=spec.instrument_id,
        session=session.upper(),
        session_date=day.isoformat(),
        start_utc=window.start_utc.isoformat(),
        end_utc=window.end_utc.isoformat(),
        asof=asof.isoformat(),
        complete=asof >= window.end_utc,
        bars=int(len(current)),
        open=round(open_price, 4),
        high=round(high, 4),
        low=round(low, 4),
        close=round(close, 4),
        volume=volume,
        vwap=round(vwap, 4) if vwap is not None else None,
        range_points=round(range_points, 4),
        return_pct=round((close / open_price - 1.0) * 100, 6) if open_price else None,
        atr=round(atr, 4) if np.isfinite(atr) else None,
        range_atr=round(range_points / atr, 4) if np.isfinite(atr) and atr > 0 else None,
        efficiency=round(float(efficiency), 4),
        volatility=round(float(returns.std()), 8) if len(returns) >= 2 else None,
        gap_pct=round(gap_pct * 100, 6) if gap_pct is not None else None,
        prior_high=round(prior_high, 4) if prior_high is not None else None,
        prior_low=round(prior_low, 4) if prior_low is not None else None,
        prior_close=round(prior_close, 4) if prior_close is not None else None,
        ib_high=round(ib_high, 4) if ib_high is not None else None,
        ib_low=round(ib_low, 4) if ib_low is not None else None,
        poc=round(poc, 4) if poc is not None else None,
        vah=round(vah, 4) if vah is not None else None,
        val=round(val, 4) if val is not None else None,
        profile_method=profile_method,
        compression=bool(np.isfinite(atr) and atr > 0 and range_points / atr < 0.8),
        data_quality={
            "bar_count": int(len(current)),
            "complete": bool(asof >= window.end_utc),
            "profile_method": profile_method,
            "event_data_available": False,
        },
    )


def session_snapshots(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    days: list[date],
    session: str,
    asof: datetime | None = None,
) -> list[SessionSnapshot]:
    snapshots = []
    for day in days:
        snapshot = session_snapshot(bars, spec, day, session, asof)
        if snapshot is not None:
            snapshots.append(snapshot)
    return snapshots


__all__ = [
    "ANALYTICAL_WINDOWS",
    "EARLY_CLOSE_DATES",
    "SessionSnapshot",
    "session_window_for",
    "session_snapshot",
    "session_snapshots",
]
