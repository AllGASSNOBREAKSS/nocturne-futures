"""Target-first competing-outcome research.

Three mutually exclusive events within a fixed bar horizon:
  1 = target reached first, 2 = stop reached first, 0 = neither (censored/timeout).

Same-bar target+stop touches are excluded as ambiguous; truncated windows are
censored, not treated as stop losses. Rows from one signal share a group and must
never be split across train/test. This module produces research evidence only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "target_atr", "stop_atr", "r_multiple", "horizon_bars",
    "hour_sin", "hour_cos", "day_of_week", "atr_pct", "atr_percentile",
    "side_long", "strategy_code",
]
EVENT_NAMES = {0: "NEITHER", 1: "TARGET_FIRST", 2: "STOP_FIRST"}


def enrich_targets(frame: pd.DataFrame, bars: pd.DataFrame, atr_window: int = 14) -> pd.DataFrame:
    """Attach point-in-time ATR and clock features at each signal's entry.

    ATR uses only bars with ``available_at <= feature_available_at``.
    """
    out = frame.copy()
    if out.empty:
        return out
    required = {"signal_id", "feature_available_at", "entry_price", "stop_price", "target_price"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    bars = bars.copy()
    for column in ("timestamp", "available_at"):
        bars[column] = pd.to_datetime(bars[column], utc=True)
    bars = bars.sort_values("timestamp").reset_index(drop=True)
    out["feature_available_at"] = pd.to_datetime(out.feature_available_at, utc=True)
    out["label_end"] = pd.to_datetime(out.label_end, utc=True)

    previous = bars.close.shift(1)
    true_range = pd.concat(
        [bars.high - bars.low, (bars.high - previous).abs(), (bars.low - previous).abs()], axis=1
    ).max(axis=1)
    atr = true_range.rolling(atr_window).mean()
    rows = []
    cache: dict[pd.Timestamp, tuple[float, float]] = {}
    for _, row in out.iterrows():
        stamp = row.feature_available_at
        if stamp not in cache:
            known = bars[bars.available_at <= stamp]
            index = len(known) - 1
            value = float(atr.iloc[index]) if index >= atr_window and np.isfinite(atr.iloc[index]) else np.nan
            history = atr.iloc[: index + 1].dropna().tail(120)
            percentile = float((history <= value).mean()) if len(history) >= 20 and np.isfinite(value) else np.nan
            cache[stamp] = (value, percentile)
        atr_points, percentile = cache[stamp]
        entry = float(row.entry_price)
        rows.append({
            "atr_points": atr_points,
            "atr_percentile": percentile,
            "atr_pct": atr_points / entry if entry else np.nan,
            "target_atr": abs(float(row.target_price) - entry) / atr_points if atr_points > 0 else np.nan,
            "stop_atr": abs(entry - float(row.stop_price)) / atr_points if atr_points > 0 else np.nan,
            "hour_sin": np.sin(2 * np.pi * stamp.hour / 24),
            "hour_cos": np.cos(2 * np.pi * stamp.hour / 24),
            "day_of_week": stamp.dayofweek,
            "side_long": int(row.get("side") == "LONG"),
            "strategy_code": pd.factorize(out.strategy_id)[0][len(rows)] if False else 0,
        })
    enrichment = pd.DataFrame(rows, index=out.index)
    out = pd.concat([out, enrichment], axis=1)
    out["strategy_code"] = pd.factorize(out.strategy_id)[0]
    out["event"] = out.outcome.map({"TP_FIRST": 1, "SL_FIRST": 2}).fillna(0).astype(int)
    out["ambiguous"] = out.outcome.eq("AMBIGUOUS")
    out["censored"] = out.outcome.isin(["CENSORED"]) | (out.outcome.eq("TIMEOUT") & ~out.horizon_complete)
    out["duration_bars"] = np.where(
        out.event.eq(1), out.bars_to_target,
        np.where(out.event.eq(2), out.bars_to_stop, out.horizon_bars - 1))
    out["duration_bars"] = pd.to_numeric(out.duration_bars, errors="coerce") + 1
    return out


def aalen_johansen(durations, events, horizon: int | None = None) -> dict:
    """Cumulative incidence for competing events with right-censoring.

    Returns the probability of each event by ``horizon`` (or the last observed
    time). Censoring includes timeouts, so the estimates are not conditional on
    an event happening.
    """
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    if durations.shape != events.shape or durations.size == 0:
        raise ValueError("durations and events must be non-empty and aligned")
    if np.any(durations < 1) or np.any(~np.isfinite(durations)):
        raise ValueError("durations must be finite and at least one bar")
    if not set(np.unique(events)).issubset({0, 1, 2}):
        raise ValueError("events must be 0 (censored), 1 or 2")
    horizon = int(durations.max()) if horizon is None else int(horizon)
    times = np.arange(1, horizon + 1)
    survival = 1.0
    incidence = {1: 0.0, 2: 0.0}
    history = []
    for time in times:
        at_risk = int((durations >= time).sum())
        if at_risk == 0:
            break
        d1 = int(((durations == time) & (events == 1)).sum())
        d2 = int(((durations == time) & (events == 2)).sum())
        censored = int(((durations == time) & (events == 0)).sum())
        # Aalen-Johansen: increments use survival *before* this time; survival
        # then drops by every removal (events and censoring), not censoring only.
        incidence[1] += survival * d1 / at_risk
        incidence[2] += survival * d2 / at_risk
        survival *= 1 - (d1 + d2 + censored) / at_risk
        history.append({"bar": int(time), "at_risk": at_risk,
                        "incidence_target": incidence[1], "incidence_stop": incidence[2],
                        "survival": survival})
    return {"horizon_bars": horizon, "incidence": {EVENT_NAMES[k]: v for k, v in incidence.items()},
            "neither": max(0.0, 1 - incidence[1] - incidence[2]),
            "at_risk_start": int(len(durations)), "path": history}


def event_rates(frame: pd.DataFrame) -> dict:
    known = frame[~frame.ambiguous & ~frame.censored]
    counts = known.event.value_counts().to_dict()
    total = len(known)
    return {"resolved_rows": total, "counts": {EVENT_NAMES[k]: int(v) for k, v in counts.items()},
            "target_share": float(counts.get(1, 0) / total) if total else None,
            "stop_share": float(counts.get(2, 0) / total) if total else None,
            "ambiguous": int(frame.ambiguous.sum()), "censored": int(frame.censored.sum())}


def outcome_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Columns follow EVENT order 1 (target), 2 (stop), 0 (neither)."""
    values = frame.event.to_numpy()
    matrix = np.zeros((len(frame), 3))
    matrix[:, 0] = values == 1
    matrix[:, 1] = values == 2
    matrix[:, 2] = values == 0
    return matrix
