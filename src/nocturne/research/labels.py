"""Triple-barrier / competing-outcome labels.

Outcomes: TP_FIRST, SL_FIRST, TIMEOUT, AMBIGUOUS. A same-bar stop+target is
ambiguous by default and excluded from the binary training set; it is never
silently counted as a win.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BarrierLabel:
    signal_index: int
    entry_index: int
    entry_time: str
    entry_price: float
    target: float
    stop: float
    outcome: str
    exit_time: str
    exit_index: int
    exit_price: float
    mfe: float
    mae: float
    bars_held: int


def triple_barrier_labels(
    bars: pd.DataFrame,
    atr: pd.Series,
    target_atr: float = 2.0,
    stop_atr: float = 1.0,
    horizon: int = 5,
    side: str = "LONG",
    entry_delay: int = 1,
    ambiguous_policy: str = "AMBIGUOUS",
) -> pd.DataFrame:
    if side not in ("LONG", "SHORT"):
        raise ValueError("side must be LONG or SHORT")
    if ambiguous_policy not in ("AMBIGUOUS", "SL_FIRST"):
        raise ValueError("ambiguous_policy must be AMBIGUOUS or SL_FIRST")

    frame = bars.reset_index(drop=True)
    atr = atr.reset_index(drop=True)
    rows: list[BarrierLabel] = []

    for i in range(len(frame) - entry_delay):
        atr_value = atr.iloc[i]
        if pd.isna(atr_value) or atr_value <= 0:
            continue
        entry_index = i + entry_delay
        entry_price = float(frame["open"].iloc[entry_index])
        if side == "LONG":
            target = entry_price + target_atr * float(atr_value)
            stop = entry_price - stop_atr * float(atr_value)
        else:
            target = entry_price - target_atr * float(atr_value)
            stop = entry_price + stop_atr * float(atr_value)

        outcome = "TIMEOUT"
        exit_index = min(entry_index + horizon, len(frame) - 1)
        exit_price = float(frame["close"].iloc[exit_index])
        mfe = 0.0
        mae = 0.0

        for j in range(entry_index, min(entry_index + horizon, len(frame) - 1) + 1):
            high = float(frame["high"].iloc[j])
            low = float(frame["low"].iloc[j])
            if side == "LONG":
                mfe = max(mfe, high - entry_price)
                mae = min(mae, low - entry_price)
                stop_hit = low <= stop
                target_hit = high >= target
            else:
                mfe = max(mfe, entry_price - low)
                mae = min(mae, entry_price - high)
                stop_hit = high >= stop
                target_hit = low <= target

            if stop_hit and target_hit:
                if ambiguous_policy == "SL_FIRST":
                    outcome, exit_index, exit_price = "SL_FIRST", j, stop
                else:
                    outcome, exit_index, exit_price = "AMBIGUOUS", j, float(frame["close"].iloc[j])
                break
            if stop_hit:
                outcome, exit_index, exit_price = "SL_FIRST", j, stop
                break
            if target_hit:
                outcome, exit_index, exit_price = "TP_FIRST", j, target
                break

        rows.append(
            BarrierLabel(
                signal_index=i,
                entry_index=entry_index,
                entry_time=str(frame["date"].iloc[entry_index]),
                entry_price=entry_price,
                target=target,
                stop=stop,
                outcome=outcome,
                exit_time=str(frame["date"].iloc[exit_index]),
                exit_index=exit_index,
                exit_price=exit_price,
                mfe=round(mfe, 6),
                mae=round(mae, 6),
                bars_held=exit_index - entry_index,
            )
        )

    return pd.DataFrame([row.__dict__ for row in rows])
