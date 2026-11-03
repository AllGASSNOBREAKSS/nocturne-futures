"""Opening Range / Initial Balance breakout with retest option.

First deterministic baseline. Signal is generated on a completed RTH bar after
the IB window; entry is the next bar open in the backtester, never the signal bar.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..auction.session import initial_balance, session_bars
from ..instruments import InstrumentSpec
from .base import Signal, StrategySpec, TargetSpec


class OpeningRangeBreakout:
    strategy_id = "opening_range_ib_breakout_retest"
    version = "0.1.0"
    spec = StrategySpec(
        strategy_id=strategy_id,
        version=version,
        instrument_id="NQ",
        session="RTH",
        entry_rule="close beyond IB high/low by buffer_ticks after IB completes",
        stop_rule="opposite side of the initial balance",
        target_rule="1R / 2R / 3R",
        horizon_bars=24,
        event_gate="NORMAL",
        data_requirements=("RTH bars", "session clock"),
    )

    def __init__(
        self,
        ib_minutes: int = 60,
        buffer_ticks: int = 2,
        target_r: tuple[float, ...] = (1.0, 2.0, 3.0),
        horizon_bars: int = 24,
        retest_only: bool = False,
    ):
        self.ib_minutes = ib_minutes
        self.buffer_ticks = buffer_ticks
        self.target_r = target_r
        self.horizon_bars = horizon_bars
        self.retest_only = retest_only

    def signals(self, bars: pd.DataFrame, spec: InstrumentSpec, day: date) -> list[Signal]:
        rth = session_bars(bars, spec, "RTH", day)
        if rth.empty:
            return []
        ib = initial_balance(rth, spec, day, minutes=self.ib_minutes)
        if not ib.complete:
            return []

        buffer = self.buffer_ticks * spec.tick_size
        after = rth[rth["timestamp"] >= ib.end]
        if after.empty:
            return []

        for _, row in after.iterrows():
            if row["close"] > ib.high + buffer:
                return [self._signal(spec, row, "LONG", ib.high, ib.low, ib.high)]
            if row["close"] < ib.low - buffer:
                return [self._signal(spec, row, "SHORT", ib.low, ib.high, ib.low)]
        return []

    def _signal(
        self,
        spec: InstrumentSpec,
        row: pd.Series,
        side: str,
        breakout_price: float,
        stop: float,
        retest_level: float,
    ) -> Signal:
        entry = float(row["close"])
        risk = abs(entry - stop)
        targets = tuple(
            TargetSpec(
                label=f"TP{i + 1}",
                price=entry + risk * r if side == "LONG" else entry - risk * r,
                r_multiple=r,
            )
            for i, r in enumerate(self.target_r)
        )
        return Signal(
            strategy_id=self.strategy_id,
            strategy_version=self.version,
            instrument_id=spec.instrument_id,
            asof=row["available_at"].to_pydatetime(),
            side=side,
            entry_low=entry,
            entry_high=entry,
            stop=stop,
            targets=targets,
            horizon_bars=self.horizon_bars,
            reason_codes=("IB_BREAKOUT", f"IB_{self.ib_minutes}M", "CLOSE_CONFIRMED"),
            data_requirements=("RTH bars",),
            metadata={
                "breakout_price": breakout_price,
                "retest_level": retest_level,
                "ib_high": float(row.get("ib_high", breakout_price)),
                "ib_low": stop,
            },
        )
