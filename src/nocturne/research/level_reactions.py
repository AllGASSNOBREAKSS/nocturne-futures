"""Price-level interaction database with distinct event definitions.

Events are intentionally separate:
  touched         bar range contains the level
  accepted        N consecutive closes beyond the level after first touch
  rejected        price returns at least ``reject_atr`` ATR to the origin side
  broke_through   price travels at least ``break_atr`` ATR beyond the level
  target_before_stop  optional barrier outcome from the touch price

Features are measured at the as-of time; outcomes use only later bars.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LevelEventConfig:
    horizon_bars: int = 48
    accept_closes: int = 3
    reject_atr: float = 0.5
    break_atr: float = 1.0
    stop_atr: float = 1.0
    target_atr: float = 2.0


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return float(max(0.0, centre - margin)), float(min(1.0, centre + margin))


def level_events(bars: pd.DataFrame, levels: list, asof: pd.Timestamp, atr: float,
                 config: LevelEventConfig | None = None) -> pd.DataFrame:
    config = config or LevelEventConfig()
    if atr <= 0:
        raise ValueError("positive ATR required")
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    frame["available_at"] = pd.to_datetime(frame.available_at, utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    known = frame[frame.available_at <= asof]
    future = frame[(frame.timestamp > asof)].head(config.horizon_bars)
    if known.empty or future.empty:
        return pd.DataFrame()
    current = float(known.close.iloc[-1])
    rows = []
    for level in levels:
        price = float(level.price)
        side = 1 if price > current else -1
        distance_atr = abs(price - current) / atr
        if distance_atr == 0:
            continue
        touched_at = None
        for position, bar in enumerate(future.itertuples(index=False)):
            if bar.low <= price <= bar.high:
                touched_at = position
                break
        row = {"level_id": level.level_id, "level_type": level.level_type,
               "price": price, "asof": asof.isoformat(), "distance_atr": distance_atr,
               "side": "ABOVE" if side > 0 else "BELOW", "touched": touched_at is not None,
               "bars_to_touch": touched_at,
               "acceptance": None, "rejection": None, "break_through": None,
               "target_before_stop": None, "mfe_atr": None, "mae_atr": None}
        if touched_at is not None:
            after = future.iloc[touched_at:]
            closes = after.close.to_numpy()
            beyond = (closes - price) * side > 0
            longest = 0
            run = 0
            for flag in beyond:
                run = run + 1 if flag else 0
                longest = max(longest, run)
            row["acceptance"] = bool(longest >= config.accept_closes)
            excursion = (after.high.max() - price) * side if side > 0 else (price - after.low.min())
            adverse = (price - after.low.min()) if side > 0 else (after.high.max() - price)
            row["mfe_atr"] = float(excursion / atr)
            row["mae_atr"] = float(adverse / atr)
            row["break_through"] = bool(excursion >= config.break_atr * atr)
            row["rejection"] = bool(adverse >= config.reject_atr * atr and excursion < config.break_atr * atr)
            # Barrier outcome from the touch: target 2 ATR beyond, stop 1 ATR back.
            target = price + side * config.target_atr * atr
            stop = price - side * config.stop_atr * atr
            outcome = "TIMEOUT"
            for bar in after.itertuples(index=False):
                hit_target = (bar.high >= target) if side > 0 else (bar.low <= target)
                hit_stop = (bar.low <= stop) if side > 0 else (bar.high >= stop)
                if hit_target and hit_stop:
                    outcome = "AMBIGUOUS"
                    break
                if hit_stop:
                    outcome = "STOP_FIRST"
                    break
                if hit_target:
                    outcome = "TARGET_FIRST"
                    break
            row["target_before_stop"] = None if outcome == "AMBIGUOUS" else outcome == "TARGET_FIRST"
            row["barrier_outcome"] = outcome
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_events(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"rows": 0}
    touched = frame[frame.touched]
    result = {"rows": len(frame), "touched": int(frame.touched.sum()),
              "touch_rate": float(frame.touched.mean()),
              "touch_interval": wilson(int(frame.touched.sum()), len(frame))}
    for event in ("acceptance", "rejection", "break_through", "target_before_stop"):
        known = touched[touched[event].notna()]
        result[event] = {"n": len(known), "count": int(known[event].sum()),
                         "rate": float(known[event].mean()) if len(known) else None,
                         "interval": wilson(int(known[event].sum()), len(known))}
    return result
