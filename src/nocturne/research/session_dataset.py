"""Session-level dataset for multi-session direction and consolidation research.

One row per completed analytical session. Features are measured at the session
close; labels use the next occurrence of the same session. The dataset is small
and must not be treated as a validated edge.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from ..instruments import InstrumentSpec
from ..market_clock import is_trading_day, next_trading_day
from ..sessions import SessionSnapshot, session_snapshot

SESSIONS = ("ASIA", "LONDON", "NEW_YORK")
NUMERIC_FEATURES = [
    "current_return_pct",
    "current_range_atr",
    "efficiency",
    "volatility",
    "gap_pct",
    "atr_pct",
    "dist_vwap_atr",
    "dist_prior_high_atr",
    "dist_prior_low_atr",
    "dist_ib_high_atr",
    "dist_ib_low_atr",
    "volume",
    "compression",
    "day_of_week",
    "es_return_pct",
    "es_nq_relative",
    "vix_level",
    "vix_change_5d",
]


def _dist(price: float | None, level: float | None, atr: float | None) -> float:
    if price is None or level is None or atr is None or atr <= 0:
        return float("nan")
    return (price - level) / atr


def _vix_context(vix: pd.DataFrame, day: date) -> tuple[float, float]:
    if vix.empty:
        return float("nan"), float("nan")
    prior = vix[vix["date"] < day.isoformat()]
    if prior.empty:
        return float("nan"), float("nan")
    level = float(prior["close"].iloc[-1])
    change = float(prior["close"].iloc[-1] / prior["close"].iloc[-6] - 1.0) if len(prior) >= 6 else float("nan")
    return level, change


def build_session_dataset(
    nq_bars: pd.DataFrame,
    es_bars: pd.DataFrame,
    vix_daily: pd.DataFrame,
    spec: InstrumentSpec,
    sessions: tuple[str, ...] = SESSIONS,
    es_spec: InstrumentSpec | None = None,
) -> pd.DataFrame:
    es_spec = es_spec or spec
    days = sorted({pd.Timestamp(value).date() for value in nq_bars["session"].unique()
                   if is_trading_day(pd.Timestamp(value).date())})
    snapshots: dict[tuple[date, str], SessionSnapshot] = {}
    for day in days:
        for session in sessions:
            snapshot = session_snapshot(nq_bars, spec, day, session)
            if snapshot is not None and snapshot.complete:
                snapshots[(day, session)] = snapshot
    es_snapshots: dict[tuple[date, str], SessionSnapshot] = {}
    for day in days:
        for session in sessions:
            snapshot = session_snapshot(es_bars, es_spec, day, session)
            if snapshot is not None and snapshot.complete:
                es_snapshots[(day, session)] = snapshot

    rows = []
    for index, day in enumerate(days[:-1]):
        next_day = next_trading_day(day)
        for session in sessions:
            current = snapshots.get((day, session))
            following = snapshots.get((next_day, session))
            if current is None or following is None:
                continue
            if not current.close or not following.close or not current.atr or current.atr <= 0:
                continue
            if not current.range_points or current.range_points <= 0:
                continue
            future_return_pct = (following.close / current.close - 1.0) * 100.0
            threshold_pct = 0.5 * current.atr / current.close * 100.0
            if future_return_pct > threshold_pct:
                direction = "BULL"
            elif future_return_pct < -threshold_pct:
                direction = "BEAR"
            else:
                direction = "NEUTRAL"
            range_ratio = following.range_points / current.range_points
            current_minutes = (pd.Timestamp(current.end_utc) - pd.Timestamp(current.start_utc)).total_seconds() / 60
            future_minutes = (pd.Timestamp(following.end_utc) - pd.Timestamp(following.start_utc)).total_seconds() / 60
            # Square-root time scaling is a research comparator, not an assumed
            # diffusion law. Keep the original same-session label unchanged.
            duration_ratio = range_ratio * np.sqrt(current_minutes / future_minutes)
            direction_scale = current.atr * np.sqrt(future_minutes / 5)
            normalized_direction = (following.close - current.close) / direction_scale
            previous_days = [d for d in days[:index] if (d, session) in snapshots]
            prior_snapshot = snapshots.get((previous_days[-1], session)) if previous_days else None
            if range_ratio <= 0.8:
                range_state = "CONSOLIDATION"
            elif range_ratio >= 1.2:
                range_state = "EXPANSION"
            else:
                range_state = "NORMAL"
            es_current = es_snapshots.get((day, session))
            es_return = es_current.return_pct if es_current and es_current.return_pct is not None else float("nan")
            vix_level, vix_change = _vix_context(vix_daily, day)
            rows.append(
                {
                    "signal_id": f"{day.isoformat()}|{session}",
                    "day": day.isoformat(),
                    "feature_available_at": current.end_utc,
                    "label_start": current.end_utc,
                    "label_end": following.end_utc,
                    "label_window_start": following.start_utc,
                    "feature_version": "session-v2-complete-5min",
                    "current_minutes": current_minutes,
                    "future_minutes": future_minutes,
                    "duration_normalized_ratio": float(duration_ratio),
                    "duration_consolidation": int(duration_ratio <= 0.8),
                    "scaled_direction": "BULL" if normalized_direction > 0.5 else "BEAR" if normalized_direction < -0.5 else "NEUTRAL",
                    "persistence_direction": "BULL" if current.return_pct > threshold_pct else "BEAR" if current.return_pct < -threshold_pct else "NEUTRAL",
                    "persistence_consolidation": int(current.range_points <= 0.8 * prior_snapshot.range_points) if prior_snapshot and prior_snapshot.range_points else None,
                    "session": session,
                    "day_of_week": day.weekday(),
                    "current_return_pct": current.return_pct,
                    "current_range_atr": current.range_atr,
                    "efficiency": current.efficiency,
                    "volatility": current.volatility,
                    "gap_pct": current.gap_pct,
                    "atr_pct": current.atr / current.close if current.close else float("nan"),
                    "dist_vwap_atr": _dist(current.close, current.vwap, current.atr),
                    "dist_prior_high_atr": _dist(current.close, current.prior_high, current.atr),
                    "dist_prior_low_atr": _dist(current.close, current.prior_low, current.atr),
                    "dist_ib_high_atr": _dist(current.close, current.ib_high, current.atr),
                    "dist_ib_low_atr": _dist(current.close, current.ib_low, current.atr),
                    "volume": current.volume,
                    "compression": int(current.compression),
                    "es_return_pct": es_return,
                    "es_nq_relative": (current.return_pct - es_return) if current.return_pct is not None and np.isfinite(es_return) else float("nan"),
                    "vix_level": vix_level,
                    "vix_change_5d": vix_change,
                    "future_return_pct": round(future_return_pct, 6),
                    "future_range_points": following.range_points,
                    "future_range_atr": following.range_points / current.atr,
                    "range_ratio": round(range_ratio, 6),
                    "direction": direction,
                    "range_state": range_state,
                    "consolidation": int(range_state == "CONSOLIDATION"),
                    "expansion": int(range_state == "EXPANSION"),
                }
            )
    return pd.DataFrame(rows)


def split_by_day(
    frame: pd.DataFrame,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    days = sorted(frame["day"].unique())
    n = len(days)
    train_end = max(1, int(n * train_fraction))
    validation_end = max(train_end + 1, int(n * (train_fraction + validation_fraction)))
    train_days = set(days[:train_end])
    validation_days = set(days[train_end:validation_end])
    test_days = set(days[validation_end:])
    return (
        frame[frame["day"].isin(train_days)].reset_index(drop=True),
        frame[frame["day"].isin(validation_days)].reset_index(drop=True),
        frame[frame["day"].isin(test_days)].reset_index(drop=True),
    )


def _dummies(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    dummies = pd.get_dummies(frame[["session"]], prefix=["session"], dtype=float)
    frame = pd.concat([frame, dummies], axis=1)
    return frame, NUMERIC_FEATURES + list(dummies.columns)


def prepare_direction(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    prepared, features = _dummies(frame.copy())
    mapping = {"BEAR": 0, "NEUTRAL": 1, "BULL": 2}
    prepared["y"] = prepared["direction"].map(mapping)
    prepared = prepared.dropna(
        subset=["y", "current_return_pct", "current_range_atr", "efficiency", "atr_pct"]
    ).reset_index(drop=True)
    return prepared, features


def prepare_consolidation(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    prepared, features = _dummies(frame.copy())
    prepared["y"] = prepared["consolidation"].astype(int)
    prepared = prepared.dropna(
        subset=["y", "current_return_pct", "current_range_atr", "efficiency", "atr_pct"]
    ).reset_index(drop=True)
    return prepared, features


__all__ = [
    "SESSIONS",
    "NUMERIC_FEATURES",
    "build_session_dataset",
    "split_by_day",
    "prepare_direction",
    "prepare_consolidation",
]
