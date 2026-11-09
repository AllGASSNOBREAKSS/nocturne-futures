"""Studio backtest jobs: existing strategies or user rules through the existing engine.

Engine rules are unchanged: next-bar-open entry, STOP_FIRST when one bar
touches stop and target, gap-through stops fill at the open, cashflow-v2
costs. Results are simulated research on research-grade continuous bars.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..auction.session import session_bars
from ..backtest.data import add_session_column
from ..backtest.engine import BacktestConfig, run_signal
from ..instruments import get_instrument
from ..strategies import OpeningRangeBreakout, ValueRejection, VWAPPullback
from . import atomic_write, market
from .rules import RuleStrategy, validate as validate_rule

BUILTIN = {"opening_range_breakout": OpeningRangeBreakout, "vwap_pullback": VWAPPullback, "value_rejection": ValueRejection}
BUILTIN_PARAMS = {"opening_range_breakout": {"ib_minutes": [15, 120, 60], "buffer_ticks": [0, 20, 2], "horizon_bars": [6, 200, 24]},
                  "vwap_pullback": {"tolerance_atr": [0.05, 2, 0.25], "stop_atr": [0.25, 5, 0.75], "horizon_bars": [6, 200, 18]},
                  "value_rejection": {"horizon_bars": [6, 200, 18], "min_excursion_ticks": [1, 40, 2]}}
INTERVALS = ("1m", "5m", "15m", "1h")


class Cancelled(Exception):
    pass


def validate(config):
    errors = []
    if config.get("root") not in market.ROOTS:
        errors.append("instrument must be NQ or ES")
    if config.get("interval") not in INTERVALS:
        errors.append(f"interval must be one of {INTERVALS}")
    strategy = config.get("strategy", {})
    kind = strategy.get("type")
    if kind == "rule":
        errors += validate_rule(strategy.get("rule", {}))
    elif kind in BUILTIN:
        if config.get("interval") not in ("1m", "5m"):
            errors.append("built-in session strategies require 1m or 5m bars")
        for key, value in (strategy.get("params") or {}).items():
            bounds = BUILTIN_PARAMS[kind].get(key)
            if bounds is None or not bounds[0] <= float(value) <= bounds[1]:
                errors.append(f"invalid parameter {key}")
    else:
        errors.append("unknown strategy type")
    costs = config.get("costs", {})
    if not 0 <= float(costs.get("commission_per_contract", 2.5)) <= 50 or not 0 <= float(costs.get("slippage_ticks", 1)) <= 20:
        errors.append("costs out of bounds")
    if int(config.get("contracts", 2)) not in (1, 2, 3, 4):
        errors.append("contracts must be 1-4")
    return errors


def _signals(config, bars, spec):
    strategy = config["strategy"]
    if strategy["type"] == "rule":
        return RuleStrategy(strategy["rule"], strategy_id=f"rule:{config.get('name', 'user')}").signals(bars, spec)
    params = dict(strategy.get("params") or {})
    for key in ("ib_minutes", "buffer_ticks", "horizon_bars", "min_excursion_ticks"):
        if key in params:
            params[key] = int(params[key])
    instance = BUILTIN[strategy["type"]](**params)
    framed = add_session_column(bars, spec)
    days = sorted(framed.session.unique())
    out = []
    for i, day in enumerate(days):
        group = framed[framed.session == day]
        if strategy["type"] == "value_rejection":
            prior = framed[framed.session == days[i - 1]] if i else None
            out += [(day, s) for s in instance.signals(group, spec, day, prior_bars=prior)]
        else:
            out += [(day, s) for s in instance.signals(group, spec, day)]
    return out


def _session_label(ts):
    hour = pd.Timestamp(ts).tz_convert("America/New_York").hour
    return "ASIA" if hour >= 18 or hour < 3 else "LONDON" if hour < 9 else "NEW_YORK" if hour < 16 else "POST"


def metrics(trades: pd.DataFrame, point_value: float):
    if trades.empty:
        return {"trades": 0}
    net = trades.net.to_numpy()
    wins, losses = net[net > 0], net[net <= 0]
    equity = np.cumsum(net)
    dd = float((np.maximum.accumulate(np.r_[0, equity]) - np.r_[0, equity]).max())
    se = net.std(ddof=1) / np.sqrt(len(net)) if len(net) > 1 else float("nan")
    outcomes = trades.outcome
    # Any target fill counts as a target touch (incl. TP_THEN_STOP / TP_THEN_TIMEOUT).
    target = ~outcomes.isin(["STOP", "TIMEOUT"])
    return {"trades": int(len(net)), "wins": int((net > 0).sum()), "losses": int((net <= 0).sum()),
            "win_rate": round(float((net > 0).mean()), 4), "loss_rate": round(float((net <= 0).mean()), 4),
            "gross_pnl": round(float(trades.gross.sum()), 2), "net_pnl": round(float(net.sum()), 2),
            "costs": round(float(trades.costs.sum()), 2),
            "profit_factor": round(float(wins.sum() / -losses.sum()), 4) if losses.sum() < 0 else None,
            "avg_win": round(float(wins.mean()), 2) if len(wins) else None, "avg_loss": round(float(losses.mean()), 2) if len(losses) else None,
            "expectancy": round(float(net.mean()), 2),
            "expectancy_ci95": [round(float(net.mean() - 1.96 * se), 2), round(float(net.mean() + 1.96 * se), 2)] if len(net) > 1 else None,
            "avg_points": round(float(trades.points.mean()), 2), "median_points": round(float(trades.points.median()), 2),
            "largest_win_points": round(float(trades.points.max()), 2), "largest_loss_points": round(float(trades.points.min()), 2),
            "max_drawdown": round(dd, 2), "avg_mfe_points": round(float(trades.mfe_points.mean()), 2),
            "avg_mae_points": round(float(trades.mae_points.mean()), 2),
            "target_hit_rate": round(float(target.mean()), 4), "stop_first_rate": round(float((outcomes == "STOP").mean()), 4),
            "timeout_rate": round(float(outcomes.str.contains("TIMEOUT").mean()), 4),
            "avg_bars_held": round(float(trades.bars_held.mean()), 2)}


def run(config, directory, progress=lambda pct, msg: None, cancelled=lambda: False):
    errors = validate(config)
    if errors:
        return {"status": "BLOCKED", "reason": "INVALID_CONFIGURATION", "errors": errors}
    spec = get_instrument(config["root"])
    bars, meta = market.bars(config["root"], config["interval"], config.get("start"), config.get("end"), limit=2_000_000)
    if len(bars) < 200:
        return {"status": "BLOCKED", "reason": "INSUFFICIENT_DATA_IN_RANGE", "rows": len(bars)}
    progress(5, f"loaded {len(bars)} bars from {meta['dataset']}")
    signals = _signals(config, bars, spec)
    progress(20, f"{len(signals)} signals generated")
    vix = market.archive().load("fred", "VIXCLS").set_index("date").value
    costs = config.get("costs", {})
    contracts = int(config.get("contracts", 2))
    schedule = ((0, 0.5), (1, 0.5)) if contracts % 2 == 0 else ((0, 1.0),)
    results, stress = [], {}
    framed = add_session_column(bars, spec) if config["strategy"]["type"] != "rule" else None
    index = pd.DatetimeIndex(bars.timestamp)
    for slip in sorted({0.5, float(costs.get("slippage_ticks", 1)), 2.0}):
        cfg = BacktestConfig(commission_per_contract=float(costs.get("commission_per_contract", 2.5)), slippage_ticks=slip,
                             contracts=contracts, cost_model="cashflow-v2", exit_schedule=schedule)
        rows = []
        for k, (day, signal) in enumerate(signals):
            if cancelled():
                raise Cancelled()
            if framed is not None:
                window = session_bars(framed[framed.session == day], spec, "RTH", day)
            else:
                start = index.searchsorted(pd.Timestamp(signal.asof))
                window = bars.iloc[start:start + signal.horizon_bars + 2]
            trade = run_signal(signal, window, spec, cfg)
            if trade is None:
                continue
            prior_vix = vix[vix.index < str(pd.Timestamp(trade.entry_time).date())]
            rows.append({"strategy": signal.strategy_id, "contract": "CONTINUOUS_FRONT_UNADJUSTED", "side": trade.side,
                         "session_date": str(day), "session": _session_label(trade.entry_time),
                         "entry_time": str(trade.entry_time), "entry": trade.entry_price, "stop": trade.stop_price,
                         "tp1": trade.target_prices[0] if trade.target_prices else None,
                         "tp2": trade.target_prices[1] if len(trade.target_prices) > 1 else None,
                         "tp3": trade.target_prices[2] if len(trade.target_prices) > 2 else None,
                         "exit_time": str(trade.exit_time), "exit": trade.exit_price, "outcome": trade.outcome,
                         "bars_held": trade.bars_held, "points": trade.points, "mfe_points": trade.mfe_points,
                         "mae_points": trade.mae_points, "gross": trade.gross_dollars, "costs": trade.costs, "net": trade.dollars,
                         "vix_prior": float(prior_vix.iloc[-1]) if len(prior_vix) else None})
            if slip == float(costs.get("slippage_ticks", 1)) and k % 50 == 0:
                progress(20 + int(60 * k / max(1, len(signals))), f"simulated {k}/{len(signals)} signals")
        stress[str(slip)] = pd.DataFrame(rows)
    trades = stress[str(float(costs.get("slippage_ticks", 1)))]
    progress(85, "computing metrics")
    point_value = spec.multiplier
    report = {"status": "SUCCEEDED", "config": config, "data": meta, "bars": len(bars), "signals": len(signals),
              "first_bar": str(bars.timestamp.iloc[0]), "last_bar": str(bars.timestamp.iloc[-1]),
              "position": f"{contracts} contracts; exit plan {schedule}", "summary": metrics(trades, point_value),
              "slippage_stress": {k: metrics(v, point_value) for k, v in stress.items()},
              "scope": "SIMULATED_RESEARCH_ON_CONTINUOUS_PROXY_NOT_ACTUAL_TRADING", "trading_decision": "NO_TRADE"}
    if not trades.empty:
        trades = trades.sort_values("entry_time").reset_index(drop=True)
        n = len(trades)
        eras = np.where(np.arange(n) < n * .5, "development", np.where(np.arange(n) < n * .75, "validation", "holdout"))
        trades["era"] = eras
        t = pd.to_datetime(trades.entry_time, utc=True)
        report["by_era"] = {e: metrics(trades[trades.era == e], point_value) for e in ("development", "validation", "holdout")}
        report["by_year"] = {str(y): metrics(g, point_value) for y, g in trades.groupby(t.dt.year)}
        report["by_month"] = {str(m): round(float(g.net.sum()), 2) for m, g in trades.groupby(t.dt.strftime("%Y-%m"))}
        report["by_session"] = {s: metrics(g, point_value) for s, g in trades.groupby("session")}
        regime = pd.cut(trades.vix_prior, [0, 15, 25, 1000], labels=["vix<15", "15-25", "vix>25"])
        report["by_regime"] = {str(r): metrics(g, point_value) for r, g in trades.groupby(regime, observed=True)}
        report["by_outcome"] = trades.outcome.value_counts().to_dict()
        report["equity_curve"] = [{"time": e, "equity": round(float(v), 2)} for e, v in zip(trades.exit_time, trades.net.cumsum())]
        report["points_histogram"] = np.histogram(trades.points, bins=20)[0].tolist()
        report["points_bins"] = [round(float(x), 2) for x in np.histogram(trades.points, bins=20)[1]]
        dev, hold = report["by_era"]["development"], report["by_era"]["holdout"]
        report["verdict"] = ("INSUFFICIENT_SAMPLE" if n < 100 else
                             "CANDIDATE_RESEARCH_ONLY" if dev.get("expectancy_ci95") and hold.get("expectancy_ci95")
                             and dev["expectancy_ci95"][0] > 0 and hold["expectancy_ci95"][0] > 0 else "REJECTED")
    else:
        report["verdict"] = "NO_TRADES"
    directory = Path(directory)
    trades.to_csv(directory / "trades.csv", index=False, lineterminator="\n")
    atomic_write(directory / "report.json", json.dumps(report, indent=2, default=str))
    progress(100, "done")
    return {"status": "SUCCEEDED", "verdict": report["verdict"], "summary": report["summary"], "report_path": str(directory / "report.json")}
