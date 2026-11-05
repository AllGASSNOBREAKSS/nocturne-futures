"""Conservative event-driven bar backtester.

Rules:
  - Signals are known at the signal bar close; entry is the next bar open.
  - If stop and target are both touched in one bar, stop wins by default.
  - Gaps through the stop fill at the open (worse), gaps through a target fill
    at the target (not better).
  - Costs: commission per side plus slippage on entry and exit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from datetime import date
from typing import Iterable

import pandas as pd

from ..instruments import InstrumentSpec
from ..strategies.base import Signal


@dataclass(frozen=True)
class BacktestConfig:
    commission_per_contract: float = 2.50
    slippage_ticks: float = 1.0
    contracts: int = 1
    ambiguous_policy: str = "STOP_FIRST"
    exit_schedule: tuple[tuple[int, float], ...] = ((0, 0.5), (1, 0.5))
    move_stop_to_breakeven_after_tp1: bool = True
    max_targets_per_bar: int = 1
    cost_model: str = "legacy-v1"


@dataclass
class TradeResult:
    strategy_id: str
    instrument_id: str
    side: str
    entry_time: pd.Timestamp
    entry_price: float
    stop_price: float
    target_prices: tuple[float, ...]
    exit_time: pd.Timestamp
    exit_price: float
    outcome: str
    points: float
    dollars: float
    gross_dollars: float
    costs: float
    risk_points: float
    mfe_points: float
    mae_points: float
    mfe_r: float
    mae_r: float
    bars_held: int
    target_fills: tuple[str, ...] = ()
    stop_moved: bool = False
    cost_model: str = "legacy-v1"


@dataclass
class BacktestReport:
    trades: list[TradeResult] = field(default_factory=list)

    def summary(self) -> dict:
        if not self.trades:
            return {
                "trades": 0,
                "wins": 0,
                "win_rate": 0.0,
                "net_dollars": 0.0,
                "net_points": 0.0,
                "profit_factor": 0.0,
                "expectancy_dollars": 0.0,
                "max_drawdown_dollars": 0.0,
            }
        wins = [t for t in self.trades if t.dollars > 0]
        losses = [t for t in self.trades if t.dollars <= 0]
        gross_win = sum(t.dollars for t in wins)
        gross_loss = abs(sum(t.dollars for t in losses))
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for trade in self.trades:
            equity += trade.dollars
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        return {
            "trades": len(self.trades),
            "wins": len(wins),
            "win_rate": round(len(wins) / len(self.trades), 4),
            "net_dollars": round(sum(t.dollars for t in self.trades), 2),
            "net_points": round(sum(t.points for t in self.trades), 2),
            "gross_win": round(gross_win, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_win / gross_loss, 4) if gross_loss else float("inf"),
            "expectancy_dollars": round(sum(t.dollars for t in self.trades) / len(self.trades), 2),
            "max_drawdown_dollars": round(max_dd, 2),
            "by_side": {
                side: {
                    "trades": len([t for t in self.trades if t.side == side]),
                    "net_dollars": round(sum(t.dollars for t in self.trades if t.side == side), 2),
                }
                for side in ("LONG", "SHORT")
            },
            "by_outcome": {
                outcome: len([t for t in self.trades if t.outcome == outcome])
                for outcome in sorted({t.outcome for t in self.trades})
            },
        }


def _entry_index(frame: pd.DataFrame, signal: Signal) -> int | None:
    future = frame[frame["timestamp"] >= signal.asof]
    if future.empty:
        return None
    return int(future.index[0])


def run_signal(
    signal: Signal,
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    config: BacktestConfig | None = None,
) -> TradeResult | None:
    config = config or BacktestConfig()
    if config.ambiguous_policy != "STOP_FIRST":
        raise ValueError("only STOP_FIRST is implemented")
    if config.contracts < 1:
        raise ValueError("contracts must be >= 1")
    if config.commission_per_contract < 0 or config.slippage_ticks < 0:
        raise ValueError("costs cannot be negative")
    if config.max_targets_per_bar < 0:
        raise ValueError("max_targets_per_bar cannot be negative")
    if sum(fraction for _, fraction in config.exit_schedule) > 1.0 + 1e-9:
        raise ValueError("exit_schedule fractions cannot exceed 1.0")

    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)

    entry_idx = _entry_index(frame, signal)
    if entry_idx is None:
        return None

    entry_bar = frame.iloc[entry_idx]
    slip = config.slippage_ticks * spec.tick_size
    direction = 1 if signal.side == "LONG" else -1
    entry_price = float(entry_bar["open"]) + direction * slip
    stop = signal.stop
    stop_moved = False
    risk_points = abs(entry_price - stop)
    target_prices = tuple(target.price for target in signal.targets)
    exit_fills = 0

    # A gap beyond the first target invalidates the entry edge; skip it.
    if direction == 1 and entry_price >= target_prices[0]:
        return None
    if direction == -1 and entry_price <= target_prices[0]:
        return None

    remaining = 1.0
    realized_points = 0.0
    target_fills: list[str] = []
    exit_time = entry_bar["timestamp"]
    exit_price = entry_price
    outcome = "TIMEOUT"
    mfe = 0.0
    mae = 0.0
    next_target = 0

    schedule = list(config.exit_schedule)
    if len(signal.targets) == 1:
        schedule = [(0, 1.0)]
    elif len(signal.targets) < 2:
        schedule = [(0, 1.0)]

    if config.cost_model not in {"legacy-v1", "cashflow-v2"}:
        raise ValueError("unknown cost accounting model")
    if config.cost_model == "cashflow-v2":
        if (not all(math.isfinite(v) for v in (config.contracts, config.slippage_ticks, config.commission_per_contract))
                or int(config.contracts) != config.contracts
                or any(not math.isfinite(fraction) or fraction <= 0 or not math.isclose(fraction * config.contracts, round(fraction * config.contracts)) for _, fraction in schedule)):
            raise ValueError("cashflow-v2 requires finite costs and whole-contract exit quantities")

    for offset in range(0, signal.horizon_bars + 1):
        idx = entry_idx + offset
        if idx >= len(frame):
            break
        bar = frame.iloc[idx]
        high, low, open_ = float(bar["high"]), float(bar["low"]), float(bar["open"])
        if direction == 1:
            mfe = max(mfe, high - entry_price)
            mae = min(mae, low - entry_price)
        else:
            mfe = max(mfe, entry_price - low)
            mae = min(mae, entry_price - high)

        stop_hit = (low <= stop) if direction == 1 else (high >= stop)
        target_hits = []
        for target_idx, fraction in schedule:
            if target_idx < next_target or target_idx >= len(signal.targets):
                continue
            target = signal.targets[target_idx]
            if (direction == 1 and high >= target.price) or (direction == -1 and low <= target.price):
                target_hits.append((target_idx, fraction, target))

        if stop_hit and target_hits and config.ambiguous_policy == "STOP_FIRST":
            target_hits = []
        if config.max_targets_per_bar > 0:
            target_hits = target_hits[: config.max_targets_per_bar]

        if stop_hit:
            fill = min(open_, stop) if direction == 1 else max(open_, stop)
            realized_points += (fill - entry_price) * direction * remaining
            exit_time, exit_price = bar["timestamp"], fill
            outcome = "STOP" if not target_fills else "TP_THEN_STOP"
            remaining = 0.0
            exit_fills += 1
            break

        for target_idx, fraction, target in target_hits:
            fill = target.price
            realized_points += (fill - entry_price) * direction * fraction
            target_fills.append(target.label)
            exit_fills += 1
            next_target = target_idx + 1
            remaining -= fraction
            exit_time, exit_price = bar["timestamp"], fill
            if remaining <= 1e-9:
                outcome = target.label
                remaining = 0.0
                break
            if config.move_stop_to_breakeven_after_tp1 and target_idx == 0:
                stop = entry_price
                stop_moved = True
        if remaining <= 1e-9:
            break

    if remaining > 1e-9:
        idx = min(entry_idx + signal.horizon_bars, len(frame) - 1)
        bar = frame.iloc[idx]
        fill = float(bar["close"])
        realized_points += (fill - entry_price) * direction * remaining
        exit_time, exit_price = bar["timestamp"], fill
        outcome = "TIMEOUT" if not target_fills else "TP_THEN_TIMEOUT"
        exit_fills += 1

    if config.cost_model == "cashflow-v2":
        # Entry fill already includes one adverse slip. Apply one quantity-
        # weighted exit slip (market-on-barrier stress, not a limit-fill claim).
        # Every entered contract is eventually fully exited; partial executions
        # do not create additional per-contract commission sides.
        realized_points -= slip
        exit_price -= direction * slip
        gross_dollars = realized_points * spec.multiplier * config.contracts
        costs = 2 * config.commission_per_contract * config.contracts
    else:
        # Preserve old report reproducibility, not an endorsement of accounting:
        # this legacy version double counts entry slip and counts fill events.
        gross_dollars = realized_points * spec.multiplier * config.contracts
        commissions = config.commission_per_contract * config.contracts * (1 + exit_fills)
        slippage_cost = 2 * slip * spec.multiplier * config.contracts
        costs = commissions + slippage_cost
    dollars = gross_dollars - costs
    return TradeResult(
        strategy_id=signal.strategy_id,
        instrument_id=signal.instrument_id,
        side=signal.side,
        entry_time=entry_bar["timestamp"],
        entry_price=round(entry_price, 4),
        stop_price=round(stop, 4),
        target_prices=target_prices,
        exit_time=exit_time,
        exit_price=round(exit_price, 4),
        outcome=outcome,
        points=round(realized_points, 4),
        dollars=round(dollars, 2),
        gross_dollars=round(gross_dollars, 2),
        costs=round(costs, 2),
        risk_points=round(risk_points, 4),
        mfe_points=round(mfe, 4),
        mae_points=round(mae, 4),
        mfe_r=round(mfe / risk_points, 4) if risk_points > 0 else 0.0,
        mae_r=round(mae / risk_points, 4) if risk_points > 0 else 0.0,
        bars_held=max(0, idx - entry_idx) if len(frame) else 0,
        target_fills=tuple(target_fills),
        stop_moved=stop_moved,
        cost_model=config.cost_model,
    )


def run_signals(
    signals: Iterable[Signal],
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    config: BacktestConfig | None = None,
) -> BacktestReport:
    report = BacktestReport()
    for signal in signals:
        result = run_signal(signal, bars, spec, config)
        if result is not None:
            report.trades.append(result)
    return report


def split_sessions(days: list[date], train_fraction: float = 0.6) -> tuple[list[date], list[date]]:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    ordered = sorted(days)
    cut = int(len(ordered) * train_fraction)
    return ordered[:cut], ordered[cut:]
