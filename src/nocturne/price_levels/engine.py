"""Significant price-level engine.

Levels are candidate zones, not guarantees. Strength combines independent
structural sources (confluence) with empirical touch/reaction counts measured
only from bars available at the as-of timestamp.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..auction.session import initial_balance, opening_range, session_bars, vwap
from ..auction.volume_profile import build_bar_approximation
from ..instruments import InstrumentSpec
from ..market_clock import ensure_utc

ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class LevelCandidate:
    level_id: str
    instrument_id: str
    level_type: str
    session: str
    price: float
    zone_low: float
    zone_high: float
    asof: str
    source: str
    confluence_count: int
    touch_count: int
    reaction_rate: float
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LevelSet:
    instrument_id: str
    asof: str
    levels: list[LevelCandidate] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "instrument_id": self.instrument_id,
            "asof": self.asof,
            "levels": [level.to_dict() for level in self.levels],
            "metadata": self.metadata,
        }


def _window(day: date, start: time, end: time) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(day, start, tzinfo=ET)
    end_dt = datetime.combine(day, end, tzinfo=ET)
    if end <= start:
        start_dt -= timedelta(days=1)
    return start_dt, end_dt


def _range(frame: pd.DataFrame) -> tuple[float, float] | None:
    if frame.empty:
        return None
    return float(frame["high"].max()), float(frame["low"].min())


def _touch_stats(
    bars: pd.DataFrame, price: float, atr: float
) -> tuple[int, float]:
    if bars.empty or atr <= 0:
        return 0, 0.0
    touches = []
    highs = bars["high"].to_numpy()
    lows = bars["low"].to_numpy()
    for i in range(len(bars)):
        if lows[i] <= price <= highs[i]:
            touches.append(i)
    if not touches:
        return 0, 0.0
    reactions = 0
    for i in touches:
        end = min(len(bars), i + 7)
        if end <= i + 1:
            continue
        future_high = float(highs[i + 1 : end].max())
        future_low = float(lows[i + 1 : end].min())
        if future_high - price >= 0.5 * atr or price - future_low >= 0.5 * atr:
            reactions += 1
    return len(touches), reactions / len(touches)


def build_levels(
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    day: date,
    asof: datetime,
    cluster_ticks: int = 8,
    max_levels: int = 40,
) -> LevelSet:
    asof = ensure_utc(asof)
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    known = frame[frame["available_at"] <= asof]
    if known.empty:
        return LevelSet(spec.instrument_id, asof.isoformat(), metadata={"reason": "NO_BARS"})

    rth = session_bars(known, spec, "RTH", day)
    if rth.empty:
        return LevelSet(spec.instrument_id, asof.isoformat(), metadata={"reason": "NO_RTH"})

    atr = float((rth["high"] - rth["low"]).tail(14).mean())
    if atr <= 0:
        atr = float((rth["high"] - rth["low"]).mean())

    sessions = sorted(known["session"].unique())
    prior_days = [s for s in sessions if s < day]
    raw: list[tuple[str, float, str, str]] = []

    def add(level_type: str, price: float | None, session: str, source: str) -> None:
        if price is not None and np.isfinite(price):
            raw.append((level_type, float(price), session, source))

    if prior_days:
        prior_day = prior_days[-1]
        prior_rth = session_bars(known[known["session"] == prior_day], spec, "RTH", prior_day)
        rng = _range(prior_rth)
        if rng:
            add("PRIOR_HIGH", rng[0], "RTH", "prior_session")
            add("PRIOR_LOW", rng[1], "RTH", "prior_session")
            add("PRIOR_CLOSE", float(prior_rth["close"].iloc[-1]), "RTH", "prior_session")
        week_days = prior_days[-5:]
        week = known[known["session"].isin(week_days)]
        rng = _range(week)
        if rng:
            add("PRIOR_WEEK_HIGH", rng[0], "COMPOSITE", "prior_week")
            add("PRIOR_WEEK_LOW", rng[1], "COMPOSITE", "prior_week")

    overnight = session_bars(known, spec, "OVERNIGHT", day)
    rng = _range(overnight)
    if rng:
        add("OVERNIGHT_HIGH", rng[0], "OVERNIGHT", "overnight")
        add("OVERNIGHT_LOW", rng[1], "OVERNIGHT", "overnight")

    for session_name, start, end in (
        ("ASIA", time(19, 0), time(3, 0)),
        ("LONDON", time(3, 0), time(8, 0)),
        ("NEW_YORK", time(8, 0), time(16, 0)),
    ):
        start_dt, end_dt = _window(day, start, end)
        subset = known[(known["timestamp"] >= start_dt) & (known["timestamp"] < end_dt)]
        rng = _range(subset)
        if rng:
            add(f"{session_name}_HIGH", rng[0], session_name, session_name.lower())
            add(f"{session_name}_LOW", rng[1], session_name, session_name.lower())

    try:
        ib = initial_balance(rth, spec, day, minutes=60, asof=asof)
        if ib.complete:
            add("IB_HIGH", ib.high, "RTH", "initial_balance")
            add("IB_LOW", ib.low, "RTH", "initial_balance")
    except ValueError:
        pass
    try:
        opening = opening_range(rth, spec, day, minutes=15, asof=asof)
        if opening.complete:
            add("OR_HIGH", opening.high, "RTH", "opening_range")
            add("OR_LOW", opening.low, "RTH", "opening_range")
    except ValueError:
        pass

    try:
        profile = build_bar_approximation(rth, spec.instrument_id, spec.tick_size, asof=asof)
        add("POC", profile.poc_price, "RTH", "volume_profile")
        add("VAH", profile.vah_price, "RTH", "volume_profile")
        add("VAL", profile.val_price, "RTH", "volume_profile")
        for bin_index in profile.hvn_bins[:3]:
            add("HVN", profile.price_of_bin(bin_index), "RTH", "volume_profile")
        for bin_index in profile.lvn_bins[:3]:
            add("LVN", profile.price_of_bin(bin_index), "RTH", "volume_profile")
    except ValueError:
        pass

    try:
        session_vwap = vwap(rth)
        add("VWAP", session_vwap, "RTH", "vwap")
        add("VWAP_UPPER", session_vwap + atr, "RTH", "volatility_band")
        add("VWAP_LOWER", session_vwap - atr, "RTH", "volatility_band")
    except ValueError:
        pass

    close = float(rth["close"].iloc[-1])
    add("VOL_UPPER", close + atr, "RTH", "volatility_band")
    add("VOL_LOWER", close - atr, "RTH", "volatility_band")

    raw.sort(key=lambda item: item[1])
    clusters: list[dict] = []
    tolerance = cluster_ticks * spec.tick_size
    for level_type, price, session, source in raw:
        if clusters and abs(price - clusters[-1]["center"]) <= tolerance:
            cluster = clusters[-1]
            cluster["prices"].append(price)
            cluster["types"].add(level_type)
            cluster["sources"].add(source)
            cluster["session"].add(session)
            cluster["center"] = float(np.mean(cluster["prices"]))
        else:
            clusters.append(
                {
                    "prices": [price],
                    "types": {level_type},
                    "sources": {source},
                    "session": {session},
                    "center": price,
                }
            )

    levels = []
    for cluster in clusters:
        price = float(np.mean(cluster["prices"]))
        touches, reaction = _touch_stats(known, price, atr)
        types = tuple(sorted(cluster["types"]))
        level_id = hashlib.sha1(
            f"{spec.instrument_id}|{types}|{price:.4f}|{asof.date()}".encode()
        ).hexdigest()[:12]
        levels.append(
            LevelCandidate(
                level_id=level_id,
                instrument_id=spec.instrument_id,
                level_type=types[0] if len(types) == 1 else "CONFLUENCE",
                session=",".join(sorted(cluster["session"])),
                price=round(price, 4),
                zone_low=round(min(cluster["prices"]), 4),
                zone_high=round(max(cluster["prices"]), 4),
                asof=asof.isoformat(),
                source=",".join(sorted(cluster["sources"])),
                confluence_count=len(types),
                touch_count=touches,
                reaction_rate=round(reaction, 4),
                sources=tuple(sorted(cluster["sources"])),
            )
        )

    levels.sort(key=lambda level: (level.confluence_count, level.reaction_rate, level.touch_count), reverse=True)
    return LevelSet(
        instrument_id=spec.instrument_id,
        asof=asof.isoformat(),
        levels=levels[:max_levels],
        metadata={
            "bar_count": int(len(known)),
            "rth_bars": int(len(rth)),
            "atr": round(atr, 4),
            "cluster_ticks": cluster_ticks,
            "profile_method": "BAR_APPROXIMATION",
            "touch_stats_point_in_time": True,
        },
    )
