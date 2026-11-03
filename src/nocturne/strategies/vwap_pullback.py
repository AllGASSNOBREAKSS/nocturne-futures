"""VWAP trend pullback with value alignment.

Trend filter: price above VWAP and VWAP rising. Pullback: the bar trades within
a tolerance of VWAP but closes above it. Entry is next-bar open in the backtester.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..auction.session import session_bars, vwap
from ..instruments import InstrumentSpec
from .base import Signal, StrategySpec, TargetSpec


class VWAPPullback:
    strategy_id = "vwap_value_aligned_pullback"
    version = "0.1.0"
    spec = StrategySpec(
        strategy_id=strategy_id,
        version=version,
        instrument_id="NQ",
        session="RTH",
        entry_rule="pullback to VWAP within tolerance, close back above, VWAP rising",
        stop_rule="recent swing low / VWAP - k*ATR",
        target_rule="1R / 2R",
        horizon_bars=18,
        event_gate="NORMAL",
        data_requirements=("RTH bars", "volume"),
    )

    def __init__(
        self,
        tolerance_atr: float = 0.25,
        stop_atr: float = 0.75,
        target_r: tuple[float, ...] = (1.0, 2.0),
        horizon_bars: int = 18,
        lookback: int = 5,
    ):
        self.tolerance_atr = tolerance_atr
        self.stop_atr = stop_atr
        self.target_r = target_r
        self.horizon_bars = horizon_bars
        self.lookback = lookback

    def signals(self, bars: pd.DataFrame, spec: InstrumentSpec, day: date) -> list[Signal]:
        rth = session_bars(bars, spec, "RTH", day)
        if len(rth) < self.lookback + 3:
            return []

        for i in range(self.lookback, len(rth)):
            history = rth.iloc[: i + 1]
            current = rth.iloc[i]
            session_vwap = vwap(history)
            prior_vwap = vwap(rth.iloc[: i + 1 - self.lookback])
            true_range = float((history["high"] - history["low"]).tail(14).mean())
            if true_range <= 0:
                continue

            rising = session_vwap > prior_vwap
            above = current["close"] > session_vwap
            touched = current["low"] <= session_vwap + self.tolerance_atr * true_range
            if not (rising and above and touched):
                continue

            entry = float(current["close"])
            stop = min(float(history["low"].tail(3).min()), session_vwap - self.stop_atr * true_range)
            risk = entry - stop
            if risk <= 0:
                continue
            targets = tuple(
                TargetSpec(
                    label=f"TP{i + 1}",
                    price=entry + risk * r,
                    r_multiple=r,
                )
                for i, r in enumerate(self.target_r)
            )
            return [
                Signal(
                    strategy_id=self.strategy_id,
                    strategy_version=self.version,
                    instrument_id=spec.instrument_id,
                    asof=current["available_at"].to_pydatetime(),
                    side="LONG",
                    entry_low=entry,
                    entry_high=entry,
                    stop=stop,
                    targets=targets,
                    horizon_bars=self.horizon_bars,
                    reason_codes=("VWAP_PULLBACK", "VWAP_RISING", "CLOSE_ABOVE_VWAP"),
                    data_requirements=("RTH bars", "volume"),
                    metadata={"vwap": session_vwap, "atr_proxy": true_range},
                )
            ]
        return []
