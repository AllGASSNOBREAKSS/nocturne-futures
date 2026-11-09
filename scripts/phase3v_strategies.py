"""Phase 3V: run the existing strategies on free Yahoo NQ=F/ES=F 5m bars.

Existing engine, unchanged rules: next-bar-open entry, STOP_FIRST on same-bar
touches, gaps through stops fill at the open, cashflow-v2 costs. Signals from
5m bars are re-run on 1m bars where 1m coverage exists (horizon scaled x5) to
measure intrabar-ordering sensitivity. Sessions split chronologically into
development / validation / holdout (50/25/25). Continuous front-month proxy;
not raw-contract fills and not forward evidence.
"""
import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.auction.session import session_bars
from nocturne.backtest.data import add_session_column
from nocturne.backtest.engine import BacktestConfig, run_signal
from nocturne.collector.store import Archive
from nocturne.instruments import get_instrument
from nocturne.strategies import OpeningRangeBreakout, ValueRejection, VWAPPullback

ROOT = Path(__file__).resolve().parents[1]
SLIPPAGE_TICKS = (0.5, 1.0, 2.0)
SPLITS = (("development", 0.5), ("validation", 0.75), ("holdout", 1.0))


def load(archive, root, interval):
    frame = archive.load("yahoo_futures", f"{root}_{interval}")
    frame = frame[frame.ohlc_consistent.astype(bool)]
    return frame[["timestamp", "available_at", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def stats(trades):
    if not trades:
        return {"trades": 0}
    net = np.array([t["dollars"] for t in trades])
    wins, losses = net[net > 0], net[net <= 0]
    equity = np.cumsum(net)
    daily = pd.Series(net, index=[str(t["session"]) for t in trades]).groupby(level=0).sum()
    outcomes = pd.Series([t["outcome"] for t in trades])
    se = net.std(ddof=1) / np.sqrt(len(net)) if len(net) > 1 else np.nan
    return {"trades": len(net), "win_rate": round(float((net > 0).mean()), 4),
            "avg_win": round(float(wins.mean()), 2) if len(wins) else None,
            "avg_loss": round(float(losses.mean()), 2) if len(losses) else None,
            "profit_factor": round(float(wins.sum() / -losses.sum()), 4) if losses.sum() < 0 else None,
            "expectancy": round(float(net.mean()), 2), "expectancy_ci95": [round(float(net.mean() - 1.96 * se), 2), round(float(net.mean() + 1.96 * se), 2)] if len(net) > 1 else None,
            "net": round(float(net.sum()), 2), "max_drawdown": round(float((np.maximum.accumulate(np.r_[0, equity]) - np.r_[0, equity]).max()), 2),
            "daily_sharpe_annualized": round(float(daily.mean() / daily.std(ddof=1) * np.sqrt(252)), 3) if len(daily) > 2 and daily.std(ddof=1) > 0 else None,
            "target_first_pct": round(float(outcomes.str.startswith("TP").mean() + outcomes.isin(["T1", "T2", "T3", "TP1", "TP2", "TP3"]).mean()), 4),
            "stop_first_pct": round(float((outcomes == "STOP").mean()), 4),
            "timeout_pct": round(float(outcomes.str.contains("TIMEOUT").mean()), 4),
            "outcomes": outcomes.value_counts().to_dict()}


def main():
    archive = Archive(ROOT / "data/history/free")
    vix = archive.load("fred", "VIXCLS").set_index("date").value
    strategies = {"opening_range_breakout": OpeningRangeBreakout(), "vwap_pullback": VWAPPullback(), "value_rejection": ValueRejection()}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "spend_usd": 0,
              "scope": "RETROSPECTIVE_CONTINUOUS_PROXY_5M_NOT_RAW_CONTRACT_FILLS",
              "position": "2 contracts: 1 exits at TP1, 1 at TP2, stop to breakeven after TP1; dollars per 2-contract position", "roots": {}}
    all_trades = []
    for root in ("NQ", "ES"):
        spec = get_instrument(root)
        five = add_session_column(load(archive, root, "5m"), spec)
        one = add_session_column(load(archive, root, "1m"), spec)
        one_sessions = {d for d, g in one.groupby("session") if len(session_bars(g, spec, "RTH", d)) >= 380}
        days = sorted(five.session.unique())
        days = [d for d in days if len(session_bars(five[five.session == d], spec, "RTH", d)) >= 76]
        cut = {name: days[min(len(days) - 1, int(len(days) * q) - 1)] for name, q in SPLITS}
        entry = {"rth_sessions": len(days), "first": str(days[0]), "last": str(days[-1]),
                 "split_end": {k: str(v) for k, v in cut.items()}, "sessions_with_full_1m_rth": len(one_sessions), "strategies": {}}
        for name, strategy in strategies.items():
            by_slip, trades_one, ordering = {}, [], {"compared": 0, "outcome_changed": 0, "net_dollars_5m": 0.0, "net_dollars_1m": 0.0}
            signals = []
            for i, day in enumerate(days):
                group = five[five.session == day]
                if name == "value_rejection":
                    prior = five[five.session == days[i - 1]] if i else None
                    signals += [(day, s) for s in strategy.signals(group, spec, day, prior_bars=prior)]
                else:
                    signals += [(day, s) for s in strategy.signals(group, spec, day)]
            for slip in SLIPPAGE_TICKS:
                config = BacktestConfig(slippage_ticks=slip, cost_model="cashflow-v2", contracts=2)  # 1 at TP1, 1 at TP2
                trades = []
                for day, signal in signals:
                    rth = session_bars(five[five.session == day], spec, "RTH", day)
                    result = run_signal(signal, rth, spec, config)
                    if result is None:
                        continue
                    era = next(k for k, v in cut.items() if day <= v)
                    record = {**dataclasses.asdict(result), "session": day, "era": era, "contract": "CONTINUOUS_FRONT_UNADJUSTED",
                              "vix_prior": float(vix[vix.index < str(day)].iloc[-1]), "slippage_ticks": slip}
                    trades.append(record)
                    if slip == 1.0 and day in one_sessions:
                        fine = session_bars(one[one.session == day], spec, "RTH", day)
                        alt = run_signal(dataclasses.replace(signal, horizon_bars=signal.horizon_bars * 5), fine, spec, config)
                        if alt is not None:
                            ordering["compared"] += 1
                            ordering["outcome_changed"] += int(alt.outcome != result.outcome)
                            ordering["net_dollars_5m"] += result.dollars
                            ordering["net_dollars_1m"] += alt.dollars
                by_slip[str(slip)] = {era: stats([t for t in trades if t["era"] == era]) for era, _ in SPLITS} | {"all": stats(trades)}
                if slip == 1.0:
                    all_trades += [{**t, "root": root, "strategy": name} for t in trades]
                    by_slip["1.0"]["by_vix"] = {label: stats([t for t in trades if f(t["vix_prior"])])
                                               for label, f in (("vix<15", lambda v: v < 15), ("15-25", lambda v: 15 <= v <= 25), ("vix>25", lambda v: v > 25))}
            ordering = {k: round(v, 2) if isinstance(v, float) else v for k, v in ordering.items()}
            dev, hold = by_slip["1.0"]["development"], by_slip["1.0"]["holdout"]
            verdict = ("INSUFFICIENT_SAMPLE" if by_slip["1.0"]["all"].get("trades", 0) < 100 else
                       "CANDIDATE" if dev.get("expectancy_ci95") and hold.get("expectancy_ci95") and dev["expectancy_ci95"][0] > 0 and hold["expectancy_ci95"][0] > 0
                       else "REJECTED")
            entry["strategies"][name] = {"signals": len(signals), "by_slippage_ticks": by_slip, "intrabar_ordering_1m": ordering, "verdict": verdict}
        report["roots"][root] = entry
    study = ROOT / "data/studies/phase3v"
    study.mkdir(parents=True, exist_ok=True)
    ledger = study / "strategy_trades.csv"
    pd.DataFrame(all_trades).to_csv(ledger, index=False, lineterminator="\n")
    report["trade_ledger"] = {"path": str(ledger.relative_to(ROOT)), "rows": len(all_trades), "sha256": hashlib.sha256(ledger.read_bytes()).hexdigest()}
    (ROOT / "reports/phase3v_strategies.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    for root, entry in report["roots"].items():
        for name, s in entry["strategies"].items():
            a = s["by_slippage_ticks"]["1.0"]["all"]
            print(root, name, s["signals"], a.get("trades"), a.get("win_rate"), a.get("profit_factor"), a.get("expectancy"), a.get("net"), s["verdict"], s["intrabar_ordering_1m"])


if __name__ == "__main__":
    main()
