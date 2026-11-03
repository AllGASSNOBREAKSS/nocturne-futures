"""Point-in-time intraday features for target-first models.

Every feature uses bars with `available_at <= signal_asof`. Prior-session and
overnight levels are known before the signal. VIX uses the prior daily close.
Missing data is explicit; no future bar is admitted.
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd

from ..auction.session import initial_balance, opening_range, session_bars, vwap
from ..auction.volume_profile import build_bar_approximation
from ..instruments import InstrumentSpec
from ..market_clock import session_date


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _safe(value: float | None) -> float:
    if value is None:
        return float("nan")
    return float(value)


def _prior_session(sessions: list[date], day: date) -> date | None:
    prior = [s for s in sessions if s < day]
    return prior[-1] if prior else None


def _session_frame(bars: pd.DataFrame, spec: InstrumentSpec, session: str, day: date) -> pd.DataFrame:
    return session_bars(bars, spec, session, day)


def build_signal_features(
    strategy_id: str,
    signal_asof: datetime,
    nq_bars: pd.DataFrame,
    es_bars: pd.DataFrame,
    vix_daily: pd.DataFrame,
    spec: InstrumentSpec,
) -> dict:
    asof = pd.Timestamp(signal_asof)
    if asof.tzinfo is None:
        asof = asof.tz_localize("UTC")
    day = session_date(asof.to_pydatetime(), spec)
    sessions = sorted(nq_bars["session"].unique())

    nq_day = nq_bars[nq_bars["session"] == day]
    rth = _session_frame(nq_day, spec, "RTH", day)
    known = rth[rth["available_at"] <= asof]
    known_all = nq_day[nq_day["available_at"] <= asof]
    if len(known_all) < 20 or len(known) < 2:
        return {}

    close = float(known["close"].iloc[-1])
    atr_series = _atr(known_all)
    atr = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else float("nan")
    if not np.isfinite(atr) or atr <= 0:
        return {}

    def dist(level: float | None) -> float:
        return (close - level) / atr if level is not None and np.isfinite(level) else float("nan")

    or15 = None
    try:
        or15 = opening_range(rth, spec, day, minutes=15, asof=asof.to_pydatetime())
    except ValueError:
        pass
    ib60 = None
    try:
        ib60 = initial_balance(rth, spec, day, minutes=60, asof=asof.to_pydatetime())
    except ValueError:
        pass

    try:
        profile = build_bar_approximation(known, spec.instrument_id, spec.tick_size, asof=asof.to_pydatetime())
        poc, vah, val = profile.poc_price, profile.vah_price, profile.val_price
        profile_method = profile.method
    except ValueError:
        poc = vah = val = float("nan")
        profile_method = "UNAVAILABLE"

    prior_day = _prior_session(sessions, day)
    prior_high = prior_low = prior_close = float("nan")
    if prior_day is not None:
        prior_rth = _session_frame(nq_bars[nq_bars["session"] == prior_day], spec, "RTH", prior_day)
        if not prior_rth.empty:
            prior_high = float(prior_rth["high"].max())
            prior_low = float(prior_rth["low"].min())
            prior_close = float(prior_rth["close"].iloc[-1])

    overnight = _session_frame(nq_day, spec, "OVERNIGHT", day)
    overnight_high = float(overnight["high"].max()) if not overnight.empty else float("nan")
    overnight_low = float(overnight["low"].min()) if not overnight.empty else float("nan")

    session_vwap = vwap(known)
    high5 = float(known_all["high"].tail(5).max())
    low5 = float(known_all["low"].tail(5).min())
    high20 = float(known["high"].tail(20).max())
    low20 = float(known["low"].tail(20).min())
    range5 = high5 - low5
    range20 = high20 - low20
    atr_percentile = float((atr_series.tail(60) <= atr).mean()) if len(atr_series.dropna()) >= 10 else float("nan")

    nq_ret_1h = close / float(known_all["close"].iloc[-13]) - 1.0 if len(known_all) >= 13 else float("nan")
    es_known = es_bars[es_bars["available_at"] <= asof]
    es_ret_1h = (
        float(es_known["close"].iloc[-1]) / float(es_known["close"].iloc[-13]) - 1.0
        if len(es_known) >= 13
        else float("nan")
    )

    vix_level = vix_change = float("nan")
    if not vix_daily.empty:
        prior_vix = vix_daily[vix_daily["date"] < day.isoformat()]
        if not prior_vix.empty:
            vix_level = float(prior_vix["close"].iloc[-1])
            if len(prior_vix) >= 6:
                vix_change = float(prior_vix["close"].iloc[-1] / prior_vix["close"].iloc[-6] - 1.0)

    return {
        "session_date": day.isoformat(),
        "time_of_day_min": (asof - pd.Timestamp(rth["timestamp"].iloc[0])).total_seconds() / 60.0,
        "close": close,
        "atr14": atr,
        "atr_pct": atr / close,
        "rv20": float(np.log(known_all["close"] / known_all["close"].shift(1)).tail(20).std()),
        "or15_size_atr": ((or15.high - or15.low) / atr) if or15 and or15.complete else float("nan"),
        "ib60_size_atr": ((ib60.high - ib60.low) / atr) if ib60 and ib60.complete else float("nan"),
        "dist_vwap_atr": dist(session_vwap),
        "dist_poc_atr": dist(poc),
        "dist_vah_atr": dist(vah),
        "dist_val_atr": dist(val),
        "dist_session_high_atr": dist(high20),
        "dist_session_low_atr": dist(low20),
        "dist_prior_high_atr": dist(prior_high),
        "dist_prior_low_atr": dist(prior_low),
        "dist_prior_close_atr": dist(prior_close),
        "dist_overnight_high_atr": dist(overnight_high),
        "dist_overnight_low_atr": dist(overnight_low),
        "mom5": close / float(known_all["close"].iloc[-6]) - 1.0 if len(known_all) >= 6 else float("nan"),
        "mom20": close / float(known_all["close"].iloc[-21]) - 1.0 if len(known_all) >= 21 else float("nan"),
        "trend_strength": (close - float(known_all["close"].tail(20).mean())) / atr,
        "range_compression": range5 / range20 if range20 > 0 else float("nan"),
        "vol_percentile": atr_percentile,
        "es_nq_relative_1h": nq_ret_1h - es_ret_1h if np.isfinite(nq_ret_1h) and np.isfinite(es_ret_1h) else float("nan"),
        "vix_level": vix_level,
        "vix_change_5d": vix_change,
        "profile_method": profile_method,
        "nq_bars": int(len(known)),
        "es_bars": int(len(es_known)),
        "vix_available": bool(np.isfinite(vix_level)),
        "event_data_available": False,
    }


def build_feature_frame(
    targets: pd.DataFrame,
    nq_bars: pd.DataFrame,
    es_bars: pd.DataFrame,
    vix_daily: pd.DataFrame,
    spec: InstrumentSpec,
) -> pd.DataFrame:
    frame = targets.copy()
    frame["signal_asof"] = pd.to_datetime(frame["signal_asof"], utc=True)
    frame["signal_id"] = (
        frame["strategy_id"].astype(str) + "|" + frame["signal_asof"].astype(str)
    )

    unique = frame[["strategy_id", "signal_asof"]].drop_duplicates()
    rows = []
    for row in unique.itertuples(index=False):
        features = build_signal_features(
            row.strategy_id,
            row.signal_asof,
            nq_bars,
            es_bars,
            vix_daily,
            spec,
        )
        if features:
            features["strategy_id"] = row.strategy_id
            features["signal_asof"] = row.signal_asof
            rows.append(features)
    feature_frame = pd.DataFrame(rows)
    if feature_frame.empty:
        return frame
    merged = frame.merge(feature_frame, on=["strategy_id", "signal_asof"], how="left")
    merged["risk_atr"] = (merged["entry_price"] - merged["stop_price"]).abs() / merged["atr14"]
    merged["target_distance_atr"] = (merged["target_price"] - merged["entry_price"]).abs() / merged["atr14"]
    return merged
