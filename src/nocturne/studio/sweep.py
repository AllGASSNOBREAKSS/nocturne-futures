"""Backtest everything: every built-in strategy, indicator preset and model signal at every RR.

All runs use the same engine, costs, contracts and date range. Results are ranked by win
rate (as requested) but each row also carries net P&L, profit factor, expectancy with a
95% interval and a two-half validation verdict, because a high win rate alone says nothing
about profit (a 1:0.25 target wins often and can still lose money).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtest.engine import BacktestConfig
from ..instruments import get_instrument
from . import atomic_write, backtest, market, modelsignals
from .rules import RuleStrategy

RR_DEFAULT = [1, 2, 3, 5, 8]


def _rule(side, conditions, label):
    return {"label": label, "family": "indicator",
            "strategy": {"type": "rule", "rule": {"side": side, "conditions": conditions, "stop": {"type": "atr", "value": 1.0},
                                                  "targets_r": [1], "horizon_bars": 48, "session": "RTH", "max_trades_per_session": 1}}}


I = lambda name, **p: {"indicator": name, "params": p}
PRESETS = [
    _rule("LONG", [{"left": I("ema", n=9), "op": "crosses_above", "right": I("ema", n=21)}], "EMA 9/21 cross up"),
    _rule("SHORT", [{"left": I("ema", n=9), "op": "crosses_below", "right": I("ema", n=21)}], "EMA 9/21 cross down"),
    _rule("LONG", [{"left": I("rsi", n=14), "op": "crosses_above", "right": 30}], "RSI 14 oversold bounce"),
    _rule("SHORT", [{"left": I("rsi", n=14), "op": "crosses_below", "right": 70}], "RSI 14 overbought fade"),
    _rule("LONG", [{"left": I("macd"), "op": "crosses_above", "right": I("macd_signal")}], "MACD bullish cross"),
    _rule("SHORT", [{"left": I("macd"), "op": "crosses_below", "right": I("macd_signal")}], "MACD bearish cross"),
    _rule("LONG", [{"left": I("close"), "op": "crosses_above", "right": I("vwap")}], "VWAP reclaim"),
    _rule("SHORT", [{"left": I("close"), "op": "crosses_below", "right": I("vwap")}], "VWAP loss"),
    _rule("LONG", [{"left": I("close"), "op": "crosses_above", "right": I("bb_upper")}], "Bollinger breakout up"),
    _rule("SHORT", [{"left": I("close"), "op": "crosses_below", "right": I("bb_lower")}], "Bollinger breakout down"),
    _rule("LONG", [{"left": I("adx"), "op": ">", "right": 25}, {"left": I("close"), "op": ">", "right": I("ema", n=50)},
                   {"left": I("close"), "op": "crosses_above", "right": I("ema", n=20)}], "ADX trend pullback long"),
    _rule("SHORT", [{"left": I("adx"), "op": ">", "right": 25}, {"left": I("close"), "op": "<", "right": I("ema", n=50)},
                    {"left": I("close"), "op": "crosses_below", "right": I("ema", n=20)}], "ADX trend pullback short"),
]
BUILTINS = [{"label": "Opening range breakout", "family": "algo", "strategy": {"type": "opening_range_breakout"}},
            {"label": "VWAP pullback", "family": "algo", "strategy": {"type": "vwap_pullback"}},
            {"label": "Value-area rejection", "family": "algo", "strategy": {"type": "value_rejection"}}]
MODELS = [
    {"label": "ML level target (09:30, p≥0.6)", "family": "model", "strategy": {"type": "ml_levels", "params": {"cutoff": "ny_open", "min_probability": 0.6}}},
    {"label": "ML level target (10:30, p≥0.6)", "family": "model", "strategy": {"type": "ml_levels", "params": {"cutoff": "post_ib", "min_probability": 0.6}}},
    {"label": "ML level target (09:30, p≥0.8)", "family": "model", "strategy": {"type": "ml_levels", "params": {"cutoff": "ny_open", "min_probability": 0.8, "min_distance_atr": 0.15}}},
    {"label": "ML next-session direction", "family": "model", "strategy": {"type": "ml_direction", "params": {"threshold": 0.55}}},
    {"label": "VWAP + ORB trend (10:30)", "family": "model", "strategy": {"type": "session_trend", "params": {"cutoff": "post_ib"}}},
    {"label": "VWAP + ORB fade (10:30)", "family": "model", "strategy": {"type": "session_trend", "params": {"cutoff": "post_ib", "fade": True}}},
]
CATALOG = BUILTINS + PRESETS + MODELS


def validate(config):
    errors = []
    if config.get("root") not in market.ROOTS:
        errors.append("instrument must be NQ or ES")
    rr = config.get("rr") or RR_DEFAULT
    if not 1 <= len(rr) <= 8 or any(not 0.25 <= float(r) <= 20 for r in rr):
        errors.append("rr: 1-8 values in [0.25, 20]")
    if not 1 <= int(config.get("contracts", 1)) <= backtest.MAX_CONTRACTS:
        errors.append(f"contracts must be 1-{backtest.MAX_CONTRACTS}")
    families = config.get("families") or ["algo", "indicator", "model"]
    if not set(families) <= {"algo", "indicator", "model"}:
        errors.append("families must be algo, indicator, model")
    return errors


def _summary(trades, point_value):
    m = backtest.metrics(trades, point_value)
    if not m.get("trades"):
        return {"trades": 0}
    t = trades.sort_values("entry_time")
    half = len(t) // 2
    first, second = backtest.metrics(t.iloc[:half], point_value), backtest.metrics(t.iloc[half:], point_value)
    ok = lambda x: bool(x.get("expectancy_ci95") and x["expectancy_ci95"][0] > 0)
    verdict = "INSUFFICIENT_SAMPLE" if len(t) < 100 else "VALIDATED_BOTH_HALVES" if ok(first) and ok(second) else \
        "PROFITABLE_NOT_SIGNIFICANT" if m["net_pnl"] > 0 else "LOSES_MONEY"
    return {k: m.get(k) for k in ("trades", "win_rate", "net_pnl", "profit_factor", "expectancy", "expectancy_ci95", "max_drawdown",
                                  "avg_win", "avg_loss", "target_hit_rate")} | {
        "first_half_net": first.get("net_pnl"), "second_half_net": second.get("net_pnl"), "verdict": verdict}


def run(config, directory, progress=lambda pct, msg: None, cancelled=lambda: False):
    errors = validate(config)
    if errors:
        return {"status": "BLOCKED", "reason": "INVALID_CONFIGURATION", "errors": errors}
    root, contracts = config["root"], int(config.get("contracts", 1))
    rr_list = sorted(float(r) for r in (config.get("rr") or RR_DEFAULT))
    start, end = config.get("start", "2019-01-01"), config.get("end")
    families = set(config.get("families") or ["algo", "indicator", "model"])
    costs = config.get("costs", {})
    spec = get_instrument(root)
    bars, meta = market.bars(root, "5m", start, end, limit=5_000_000, source="databento")
    progress(3, f"loaded {len(bars)} authentic 5m bars")
    vix = market.archive().load("fred", "VIXCLS").set_index("date").value
    groups = backtest.sessions_of(bars, spec)
    items = [c for c in CATALOG if c["family"] in families]
    total, done, rows = len(items) * len(rr_list), 0, []
    for item in items:
        kind = item["strategy"]["type"]
        base_cfg = {"root": root, "interval": "5m", "source": "databento", "start": start, "end": end, "contracts": contracts,
                    "costs": costs, "strategy": item["strategy"], "name": item["label"]}
        cached_builtin = backtest._signals(base_cfg, bars, spec) if kind in backtest.BUILTIN else None
        for rr in rr_list:
            if cancelled():
                raise backtest.Cancelled()
            exit_cfg = {"rr": [rr]}
            if kind in modelsignals.KINDS and kind != "ml_levels":
                exit_cfg["stop"] = config.get("model_stop") or {"type": "atr", "value": 0.25}
            cfg = {**base_cfg, "exit": exit_cfg}
            try:
                signals = backtest.apply_exit(cached_builtin, exit_cfg) if cached_builtin is not None else backtest._signals(cfg, bars, spec)
                engine = BacktestConfig(commission_per_contract=float(costs.get("commission_per_contract", 2.5)),
                                        slippage_ticks=float(costs.get("slippage_ticks", 1)), contracts=contracts, cost_model="cashflow-v2",
                                        exit_schedule=((0, 1.0),))
                trades = backtest.simulate(signals, bars, spec, engine, groups if kind in backtest.BUILTIN else None, cancelled, vix=vix)
                summary = _summary(trades, spec.multiplier)
            except backtest.Cancelled:
                raise
            except Exception as exc:  # one failing family must not sink the sweep
                summary = {"trades": 0, "error": f"{type(exc).__name__}: {exc}"[:200]}
            rows.append({"label": item["label"], "family": item["family"], "rr": rr, "config": cfg, **summary})
            done += 1
            progress(3 + int(95 * done / total), f"{item['label']} 1:{rr:g} -> {summary.get('trades', 0)} trades")
    board = pd.DataFrame(rows)
    traded = board[board.trades >= 100] if len(board) else board
    best = lambda col: (traded.sort_values(col, ascending=False).iloc[0].to_dict() if len(traded) else None)
    report = {"status": "SUCCEEDED", "config": config, "data": meta, "bars": len(bars), "first_bar": str(bars.timestamp.iloc[0]),
              "last_bar": str(bars.timestamp.iloc[-1]), "contracts": contracts, "rr": rr_list,
              "leaderboard": sorted(rows, key=lambda r: (-(r.get("win_rate") or 0), -(r.get("net_pnl") or -1e18))),
              "highest_win_rate": best("win_rate"), "highest_net_pnl": best("net_pnl"),
              "validated": [r for r in rows if r.get("verdict") == "VALIDATED_BOTH_HALVES"],
              "note": "Ranked by win rate as requested; check net P&L and the verdict - win rate rises as reward:risk falls.",
              "scope": "SIMULATED_RESEARCH_ON_AUTHENTIC_CONTRACT_BARS_NOT_ACTUAL_TRADING", "trading_decision": "NO_TRADE"}
    atomic_write(Path(directory) / "report.json", json.dumps(report, indent=2, default=str))
    pd.DataFrame([{k: v for k, v in r.items() if k != "config"} for r in rows]).to_csv(Path(directory) / "trades.csv", index=False)
    progress(100, "done")
    return report
