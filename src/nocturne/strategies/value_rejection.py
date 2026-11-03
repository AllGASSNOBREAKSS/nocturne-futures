"""Prior VAH/VAL failed-auction / rejection candidate.

Requires a prior completed profile. The bar approximation is accepted only when
the profile is explicitly labelled as such; true trade profiles are preferred.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..auction.session import session_bars
from ..auction.volume_profile import VolumeProfile, build_bar_approximation
from ..instruments import InstrumentSpec
from .base import Signal, StrategySpec, TargetSpec


class ValueRejection:
    strategy_id = "vah_val_failed_auction"
    version = "0.1.0"
    spec = StrategySpec(
        strategy_id=strategy_id,
        version=version,
        instrument_id="NQ",
        session="RTH",
        entry_rule="excursion beyond prior VAH/VAL followed by close back inside value",
        stop_rule="beyond the excursion extreme",
        target_rule="prior POC",
        horizon_bars=18,
        event_gate="NORMAL",
        data_requirements=("prior session profile", "RTH bars"),
    )

    def __init__(self, horizon_bars: int = 18, min_excursion_ticks: int = 2):
        self.horizon_bars = horizon_bars
        self.min_excursion_ticks = min_excursion_ticks

    def prior_profile(
        self, prior_bars: pd.DataFrame, spec: InstrumentSpec
    ) -> VolumeProfile:
        return build_bar_approximation(prior_bars, spec.instrument_id, spec.tick_size)

    def signals(
        self,
        bars: pd.DataFrame,
        spec: InstrumentSpec,
        day: date,
        prior_bars: pd.DataFrame | None = None,
        prior_profile: VolumeProfile | None = None,
    ) -> list[Signal]:
        if prior_profile is None:
            if prior_bars is None or prior_bars.empty:
                return []
            prior_profile = self.prior_profile(prior_bars, spec)

        rth = session_bars(bars, spec, "RTH", day)
        if rth.empty:
            return []

        buffer = self.min_excursion_ticks * spec.tick_size
        vah, val, poc = prior_profile.vah_price, prior_profile.val_price, prior_profile.poc_price
        for _, row in rth.iterrows():
            high, low, close = float(row["high"]), float(row["low"]), float(row["close"])
            if high > vah + buffer and close < vah:
                return [self._signal(spec, row, "SHORT", high, vah, poc)]
            if low < val - buffer and close > val:
                return [self._signal(spec, row, "LONG", low, val, poc)]
        return []

    def _signal(
        self,
        spec: InstrumentSpec,
        row: pd.Series,
        side: str,
        excursion: float,
        value_edge: float,
        poc: float,
    ) -> Signal:
        entry = float(row["close"])
        stop = excursion - 2 * spec.tick_size if side == "LONG" else excursion + 2 * spec.tick_size
        risk = abs(entry - stop)
        target_price = poc if (side == "LONG" and poc > entry) or (side == "SHORT" and poc < entry) else entry + risk if side == "LONG" else entry - risk
        r_multiple = abs(target_price - entry) / risk if risk > 0 else 0.0
        return Signal(
            strategy_id=self.strategy_id,
            strategy_version=self.version,
            instrument_id=spec.instrument_id,
            asof=row["available_at"].to_pydatetime(),
            side=side,
            entry_low=entry,
            entry_high=entry,
            stop=stop,
            targets=(TargetSpec(label="POC", price=target_price, r_multiple=r_multiple),),
            horizon_bars=self.horizon_bars,
            reason_codes=("FAILED_AUCTION", f"VALUE_{'VAH' if side == 'SHORT' else 'VAL'}", "CLOSE_BACK_IN_VALUE"),
            data_requirements=("prior session profile",),
            metadata={"value_edge": value_edge, "poc": poc, "profile_method": "BAR_APPROXIMATION"},
        )
