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
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
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
        if risk <= 0:
            continue
        if config.target_multiples:
            targets = [
                (f"TP{i + 1}", entry + direction * risk * multiple, multiple)
                for i, multiple in enumerate(config.target_multiples)
            ]
        else:
            targets = [(t.label, t.price, t.r_multiple) for t in signal.targets]
        end_idx = min(entry_idx + config.horizon_bars, len(frame) - 1)

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

            rows.append(
                {
                    "strategy_id": signal.strategy_id,
                    "instrument_id": signal.instrument_id,
                    "signal_asof": signal.asof,
                    "side": signal.side,
                    "entry_time": entry_bar["timestamp"],
                    "entry_price": round(entry, 4),
                    "stop_price": round(stop, 4),
                    "target_id": label,
                    "target_price": round(target_price, 4),
                    "r_multiple": round(abs(target_price - entry) / risk, 4),
                    "horizon_bars": config.horizon_bars,
                    "outcome": outcome,
                    "target_first": outcome == "TP_FIRST",
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
