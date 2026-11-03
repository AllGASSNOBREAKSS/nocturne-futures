"""Held-out, cost-stressed strategy study for Phase 3A."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from ..auction.session import session_bars
from ..instruments import get_instrument
from ..strategies.opening_range import OpeningRangeBreakout
from ..strategies.value_rejection import ValueRejection
from ..strategies.vwap_pullback import VWAPPullback
from .data import ROOT, add_session_column, load_intraday
from .engine import BacktestConfig, BacktestReport, run_signal

STRATEGIES = ("orb", "vwap", "value")


def _signals(
    name: str,
    bars: pd.DataFrame,
    spec,
    sessions: list[date],
) -> dict[date, list]:
    out: dict[date, list] = {}
    for index, day in enumerate(sessions):
        group = bars[bars["session"] == day]
        rth = session_bars(group, spec, "RTH", day)
        if rth.empty:
            out[day] = []
            continue
        if name == "orb":
            out[day] = OpeningRangeBreakout().signals(group, spec, day)
        elif name == "vwap":
            out[day] = VWAPPullback().signals(group, spec, day)
        elif name == "value":
            if index == 0:
                out[day] = []
            else:
                prior_day = sessions[index - 1]
                prior_rth = session_bars(
                    bars[bars["session"] == prior_day], spec, "RTH", prior_day
                )
                out[day] = ValueRejection().signals(
                    group, spec, day, prior_bars=prior_rth
                )
        else:
            raise ValueError(name)
    return out


def generate_signals(
    name: str,
    bars: pd.DataFrame,
    spec,
    sessions: list[date],
) -> dict[date, list]:
    return _signals(name, bars, spec, sessions)


def build_dataset(
    name: str,
    instrument: str,
    force: bool = False,
    horizon_bars: int = 24,
    target_multiples: tuple[float, ...] | None = None,
    target_points: tuple[float, ...] | None = None,
    slippage_ticks: float = 0.0,
) -> tuple[pd.DataFrame, dict]:
    from ..research.target_dataset import TargetDatasetConfig, build_strategy_target_dataset

    spec = get_instrument(instrument)
    bars, meta = load_intraday(instrument, force=force)
    bars = add_session_column(bars, spec)
    sessions = sorted(bars["session"].unique())
    signals = _signals(name, bars, spec, sessions)
    frames = []
    for day in sessions:
        rth = session_bars(bars[bars["session"] == day], spec, "RTH", day)
        frames.append(
            build_strategy_target_dataset(
                signals.get(day, []),
                rth,
                spec,
                TargetDatasetConfig(horizon_bars=horizon_bars, target_multiples=target_multiples,
                                    target_points=target_points, slippage_ticks=slippage_ticks),
            )
        )
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return frame, meta


def _run(
    bars: pd.DataFrame,
    spec,
    sessions: list[date],
    signals: dict[date, list],
    config: BacktestConfig,
) -> BacktestReport:
    report = BacktestReport()
    for day in sessions:
        rth = session_bars(bars[bars["session"] == day], spec, "RTH", day)
        for signal in signals.get(day, []):
            result = run_signal(signal, rth, spec, config)
            if result is not None:
                report.trades.append(result)
    return report


def run_study(
    name: str,
    instrument: str,
    holdout_fraction: float = 0.4,
    force: bool = False,
) -> dict:
    spec = get_instrument(instrument)
    bars, meta = load_intraday(instrument, force=force)
    bars = add_session_column(bars, spec)
    sessions = sorted(bars["session"].unique())
    if len(sessions) < 10:
        raise ValueError("not enough sessions for a study")

    cut = int(len(sessions) * (1 - holdout_fraction))
    splits = {
        "development": sessions[:cut],
        "holdout": sessions[cut:],
    }
    signals = _signals(name, bars, spec, sessions)

    result: dict = {
        "strategy": name,
        "instrument": instrument.upper(),
        "data": meta,
        "sessions": {"total": len(sessions), "development": len(splits["development"]), "holdout": len(splits["holdout"])},
        "splits": {},
    }
    for split_name, days in splits.items():
        split_result = {}
        for slip in (1, 2, 3, 4):
            config = replace(BacktestConfig(), slippage_ticks=float(slip))
            report = _run(bars, spec, days, signals, config)
            summary = report.summary()
            split_result[f"slip_{slip}"] = summary
            if slip == 1:
                split_result["trades"] = [trade.__dict__ for trade in report.trades]
        result["splits"][split_name] = split_result
    return result


def save_study(result: dict, root: Path | None = None) -> Path:
    root = root or ROOT / "reports"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"phase3a_{result['instrument']}_{result['strategy']}.json"
    path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def run_all(force: bool = False) -> list[dict]:
    results = []
    for instrument in ("NQ", "ES"):
        for name in STRATEGIES:
            result = run_study(name, instrument, force=force)
            save_study(result)
            results.append(result)
    return results


def markdown(results: list[dict]) -> str:
    lines = [
        "# Phase 3A Backtest Study",
        "",
        "Chronological development (first 60%) and holdout (last 40%).",
        "Costs: $2.50/contract/side, 1-tick base slippage; stress at 2/3/4 ticks.",
        "ORB exits are capped at the RTH session; targets are 1R/2R/3R.",
        "",
        "| Instrument | Strategy | Split | Trades | Win % | Net $ | PF | Max DD $ | Timeouts |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        for split in ("development", "holdout"):
            summary = result["splits"][split]["slip_1"]
            lines.append(
                f"| {result['instrument']} | {result['strategy']} | {split} | "
                f"{summary['trades']} | {100 * summary['win_rate']:.1f} | "
                f"{summary['net_dollars']:.2f} | {summary['profit_factor']:.3f} | "
                f"{summary['max_drawdown_dollars']:.2f} | "
                f"{summary.get('by_outcome', {}).get('TIMEOUT', 0)} |"
            )
    lines.extend(
        [
            "",
            "## Cost stress (holdout, net dollars)",
            "",
            "| Instrument | Strategy | 1 tick | 2 ticks | 3 ticks | 4 ticks |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for result in results:
        cells = []
        for slip in (1, 2, 3, 4):
            cells.append(f"{result['splits']['holdout'][f'slip_{slip}']['net_dollars']:.2f}")
        lines.append(
            f"| {result['instrument']} | {result['strategy']} | " + " | ".join(cells) + " |"
        )
    lines.append("")
    return "\n".join(lines)
