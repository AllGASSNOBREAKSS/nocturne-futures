"""Target-level training dataset.

One row per (signal, candidate target). Records the entry, stop, target,
horizon, target-first outcome, MFE and MAE. This is the interface for the next
target-probability model; it is not a model and it does not imply an edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from ..instruments import InstrumentSpec
from ..strategies.base import Signal


@dataclass(frozen=True)
class TargetDatasetConfig:
    horizon_bars: int = 24
    ambiguous_policy: str = "AMBIGUOUS"
    slippage_ticks: float = 0.0
    target_multiples: tuple[float, ...] | None = None
    target_points: tuple[float, ...] | None = None
    commission_per_side: float = 2.5
    interval: str = "5min"


def _entry_index(frame: pd.DataFrame, asof: datetime) -> int | None:
    future = frame[frame["timestamp"] >= asof]
    if future.empty:
        return None
    return int(future.index[0])


def build_strategy_target_dataset(
    signals: list[Signal],
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    config: TargetDatasetConfig | None = None,
) -> pd.DataFrame:
    config = config or TargetDatasetConfig()
    if config.horizon_bars < 1:
        raise ValueError("horizon must be positive")
    if config.slippage_ticks < 0 or config.commission_per_side < 0:
        raise ValueError("costs must be nonnegative")
    if config.target_points and (config.target_multiples or min(config.target_points) <= 0):
        raise ValueError("positive point targets must be separate from R targets")
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    slip = config.slippage_ticks * spec.tick_size
    rows: list[dict] = []

    for signal in signals:
        entry_idx = _entry_index(frame, signal.asof)
        if entry_idx is None:
            continue
        entry_bar = frame.iloc[entry_idx]
        direction = 1 if signal.side == "LONG" else -1
        entry = float(entry_bar["open"]) + direction * slip
        stop = signal.stop
        risk = abs(entry - stop)
        if risk <= 0 or direction * (entry - stop) <= 0:
            continue
        if config.target_points:
            targets = [(f"POINTS_{points:g}", entry + direction * points, points / risk)
                       for points in config.target_points]
        elif config.target_multiples:
            targets = [
                (f"TP{i + 1}", entry + direction * risk * multiple, multiple)
                for i, multiple in enumerate(config.target_multiples)
            ]
        else:
            targets = [(t.label, t.price, t.r_multiple) for t in signal.targets]
        end_idx = min(entry_idx + config.horizon_bars - 1, len(frame) - 1)
        complete = end_idx - entry_idx + 1 == config.horizon_bars
        timestamps = frame.timestamp.iloc[entry_idx:end_idx + 1]
        contiguous = timestamps.diff().dropna().eq(pd.Timedelta(config.interval)).all()
        gaps = timestamps.diff().dropna().ne(pd.Timedelta(config.interval)).to_numpy()
        prefix_bars = next((i + 1 for i, gap in enumerate(gaps) if gap), len(timestamps))
        complete = complete and contiguous

        stop_idx: int | None = None
        target_idx: dict[int, int] = {}
        mfe = 0.0
        mae = 0.0
        for j in range(entry_idx, end_idx + 1):
            high = float(frame["high"].iloc[j])
            low = float(frame["low"].iloc[j])
            if direction == 1:
                mfe = max(mfe, high - entry)
                mae = min(mae, low - entry)
                if stop_idx is None and low <= stop:
                    stop_idx = j
                for i, target in enumerate(targets):
                    if i not in target_idx and high >= target[1]:
                        target_idx[i] = j
            else:
                mfe = max(mfe, entry - low)
                mae = min(mae, entry - high)
                if stop_idx is None and high >= stop:
                    stop_idx = j
                for i, target in enumerate(targets):
                    if i not in target_idx and low <= target[1]:
                        target_idx[i] = j

        for i, target in enumerate(targets):
            label, target_price, target_r = target
            if direction * (target_price - entry) <= 0:
                continue  # opening gap already beyond target: no reachable entry setup
            t_idx = target_idx.get(i)
            if t_idx is None and stop_idx is None:
                outcome = "TIMEOUT"
            elif t_idx is None:
                outcome = "SL_FIRST"
            elif stop_idx is None:
                outcome = "TP_FIRST"
            elif t_idx == stop_idx:
                outcome = "AMBIGUOUS" if config.ambiguous_policy == "AMBIGUOUS" else "SL_FIRST"
            elif t_idx < stop_idx:
                outcome = "TP_FIRST"
            else:
                outcome = "SL_FIRST"
            if not contiguous or (outcome == "TIMEOUT" and not complete):
                outcome = "CENSORED"

            # Each row is a separate hypothetical full-size exit, never a
            # portfolio or partial-exit ledger. Gap stops fill adversely at open.
            exit_idx = None
            exit_price = None
            if outcome == "TP_FIRST":
                exit_idx, exit_price = t_idx, target_price
            elif outcome == "SL_FIRST":
                exit_idx = stop_idx
                opening = float(frame.open.iloc[stop_idx])
                exit_price = min(stop, opening) if direction == 1 else max(stop, opening)
            elif outcome == "TIMEOUT":
                exit_idx, exit_price = end_idx, float(frame.close.iloc[end_idx])
            if exit_price is not None:
                exit_price -= direction * slip
            net = (direction * (exit_price - entry) * spec.multiplier
                   - 2 * config.commission_per_side) if exit_price is not None else None

            rows.append(
                {
                    "strategy_id": signal.strategy_id,
                    "instrument_id": signal.instrument_id,
                    "signal_asof": signal.asof,
                    "signal_id": f"{signal.instrument_id}|{signal.strategy_id}|{signal.asof.isoformat()}",
                    "feature_available_at": signal.asof,
                    "label_end": frame.available_at.iloc[end_idx],
                    "label_definition": "target-before-stop-within-h-bars-v2",
                    "horizon_complete": bool(complete),
                    "observed_bars": int(len(timestamps)),
                    "observed_contiguous_bars": int(prefix_bars),
                    "bar_interval": config.interval,
                    "excursion_definition": "full_observed_horizon_not_executable_exit_pnl",
                    "side": signal.side,
                    "entry_time": entry_bar["timestamp"],
                    "entry_price": round(entry, 4),
                    "stop_price": round(stop, 4),
                    "target_id": label,
                    "target_price": round(target_price, 4),
                    "r_multiple": round(abs(target_price - entry) / risk, 4),
                    "horizon_bars": config.horizon_bars,
                    "outcome": outcome,
                    "target_first": None if outcome in {"CENSORED", "AMBIGUOUS"} else outcome == "TP_FIRST",
                    "target_touched": (t_idx is not None) if contiguous and (complete or t_idx is not None) else None,
                    "touch_definition": "bar_extreme_reaches_target_even_after_stop",
                    "exit_price": exit_price,
                    "exit_time": frame.available_at.iloc[exit_idx] if exit_idx is not None else None,
                    "hypothetical_net_dollars": net,
                    "commission_round_trip": 2 * config.commission_per_side,
                    "slippage_ticks_per_side": config.slippage_ticks,
                    "cost_definition": "one_contract_independent_candidate_not_portfolio_pnl",
                    "bars_to_target": (t_idx - entry_idx) if t_idx is not None else None,
                    "bars_to_stop": (stop_idx - entry_idx) if stop_idx is not None else None,
                    "mfe_points": round(mfe, 4),
                    "mae_points": round(mae, 4),
                    "mfe_r": round(mfe / risk, 4),
                    "mae_r": round(mae / risk, 4),
                }
            )
    return pd.DataFrame(rows)


def save_target_dataset(frame: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
