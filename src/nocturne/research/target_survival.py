"""Target-first competing-outcome research.

Two competing events within a fixed bar horizon:
  1 = target reached first, 2 = stop reached first, 0 = right censoring.
Observed no-event horizon completion is distinct from lost observation time.

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

    rows = []
    cache: dict[pd.Timestamp, tuple[float, float]] = {}
    for _, row in out.iterrows():
        stamp = row.feature_available_at
        if stamp not in cache:
            known = bars[bars.available_at <= stamp]
            previous = known.close.shift(1)
            true_range = pd.concat([known.high - known.low, (known.high - previous).abs(),
                                    (known.low - previous).abs()], axis=1).max(axis=1)
            observed_atr = true_range.rolling(atr_window).mean()
            value = float(observed_atr.iloc[-1]) if len(known) > atr_window and np.isfinite(observed_atr.iloc[-1]) else np.nan
            history = observed_atr.dropna().tail(120)
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
    out["duration_bars"] = pd.to_numeric(out.duration_bars, errors="coerce").astype(float) + 1
    # A truncated/gapped window cannot be censored at its intended full horizon.
    observed = out.get("observed_contiguous_bars", pd.Series(np.nan, index=out.index))
    out.loc[out.censored, "duration_bars"] = observed[out.censored]
    out["duration_evidence"] = np.where(out.censored & out.duration_bars.isna(),
                                       "UNKNOWN_OBSERVATION_END_EXCLUDE_FROM_SURVIVAL", "OBSERVED")
    return out


def aalen_johansen(durations, events, horizon: int | None = None) -> dict:
    """Cumulative incidence for competing events with right-censoring.

    Returns the probability of each event by ``horizon`` (or the last observed
    time). Censoring includes timeouts, so the estimates are not conditional on
    an event happening.
    """
    durations = np.asarray(durations, dtype=float)
    raw_events = np.asarray(events, dtype=float)
    if durations.shape != raw_events.shape or durations.size == 0 or durations.ndim != 1:
        raise ValueError("durations and events must be non-empty and aligned")
    if np.any(durations < 1) or np.any(~np.isfinite(durations)) or np.any(durations != np.floor(durations)):
        raise ValueError("durations must be finite integer bar counts of at least one")
    if not np.isfinite(raw_events).all() or np.any(raw_events != np.floor(raw_events)):
        raise ValueError("events must be integer codes")
    events = raw_events.astype(int)
    if not set(np.unique(events)).issubset({0, 1, 2}):
        raise ValueError("events must be 0 (censored), 1 or 2")
    if horizon is not None and (not np.isfinite(horizon) or horizon < 1 or int(horizon) != horizon):
        raise ValueError("horizon must be a positive integer bar count")
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
        # then drops only on events. Censoring removes observations from later
        # risk sets but is not a failure hazard. Tied events precede censoring.
        incidence[1] += survival * d1 / at_risk
        incidence[2] += survival * d2 / at_risk
        survival *= 1 - (d1 + d2) / at_risk
        history.append({"bar": int(time), "at_risk": at_risk,
                        "incidence_target": incidence[1], "incidence_stop": incidence[2],
                         "survival": survival, "censored": censored})
    return {"horizon_bars": horizon, "incidence": {EVENT_NAMES[k]: v for k, v in incidence.items()},
            "neither": max(0.0, 1 - incidence[1] - incidence[2]),
            "at_risk_start": int(len(durations)), "path": history,
            "event_free_survival": survival,
            "horizon_supported": bool(durations.max() >= horizon),
            "estimator_version": "aj-discrete-v2-event-only-survival",
            "assumption": "non-informative censoring; no extrapolated event hazard beyond observed support"}


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
