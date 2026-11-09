"""Phase 4: existing strategies on authentic Databento NQ/ES 5m bars, 2010 -> 2026.

Strategy parameters are the existing defaults (no optimisation). Chronological
date eras: development 2010-06..2018, validation 2019..2022, holdout 2023..2026.
Writes reports/phase4_backtests.json/.md and keeps ledgers under ignored
data/studio/phase4_backtests/ (licensed-derived).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nocturne.studio import backtest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/studio/phase4_backtests"
ERAS = {"development": ("2010-01-01", "2019-01-01"), "validation": ("2019-01-01", "2023-01-01"), "holdout": ("2023-01-01", "2027-01-01")}


def verdict(eras):
    d, h = eras["development"], eras["holdout"]
    if d.get("trades", 0) < 100 or h.get("trades", 0) < 100:
        return "INSUFFICIENT_SAMPLE"
    if d.get("expectancy_ci95") and h.get("expectancy_ci95") and d["expectancy_ci95"][0] > 0 and h["expectancy_ci95"][0] > 0:
        return "CANDIDATE_RESEARCH_ONLY"
    return "REJECTED"


def main():
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "data": "Databento GLBX.MDP3 ohlcv-1m front-month (v.0) aggregated to 5m within contract",
              "eras": ERAS, "position": "2 contracts: 1 at TP1, 1 at TP2, stop to breakeven after TP1; cashflow-v2 costs",
              "scope": "SIMULATED_RESEARCH_NOT_ACTUAL_TRADING", "trading_decision": "NO_TRADE", "results": {}}
    for root in ("NQ", "ES"):
        for strategy in ("opening_range_breakout", "vwap_pullback", "value_rejection"):
            name = f"{root}_{strategy}"
            folder = OUT / name
            folder.mkdir(parents=True, exist_ok=True)
            result = backtest.run({"name": name, "root": root, "interval": "5m", "source": "databento", "contracts": 2,
                                   "costs": {"commission_per_contract": 2.5, "slippage_ticks": 1}, "strategy": {"type": strategy}}, folder)
            full = json.loads((folder / "report.json").read_text())
            trades = pd.read_csv(folder / "trades.csv")
            t = pd.to_datetime(trades.entry_time, utc=True)
            eras = {era: backtest.metrics(trades[(t >= pd.Timestamp(a, tz="UTC")) & (t < pd.Timestamp(b, tz="UTC"))], 0) for era, (a, b) in ERAS.items()}
            report["results"][name] = {"summary": full["summary"], "eras": eras, "by_year": full.get("by_year"), "by_session": full.get("by_session"),
                                       "by_regime": full.get("by_regime"), "slippage_stress": full.get("slippage_stress"),
                                       "by_outcome": full.get("by_outcome"), "signals": full["signals"], "bars": full["bars"],
                                       "first_bar": full["first_bar"], "last_bar": full["last_bar"], "verdict": verdict(eras)}
            s = full["summary"]
            print(name, s.get("trades"), s.get("win_rate"), s.get("profit_factor"), s.get("expectancy"), s.get("net_pnl"), report["results"][name]["verdict"], flush=True)
    (ROOT / "reports/phase4_backtests.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    lines = ["# Phase 4 — 16-year strategy backtests on authentic NQ/ES contract bars", "", f"Generated {report['generated_at']}. {report['data']}.",
             f"{report['position']}. Eras: development 2010–2018, validation 2019–2022, holdout 2023–2026. {report['scope']}; NO_TRADE.", "",
             "| Strategy | Trades | Win % | PF | Expectancy $ | Net $ | Max DD $ | Target touched | Dev exp [CI] | Val exp | Holdout exp [CI] | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in report["results"].items():
        s, e = r["summary"], r["eras"]
        ci = lambda m: f"{m.get('expectancy', 'n/a')} [{m['expectancy_ci95'][0]}, {m['expectancy_ci95'][1]}]" if m.get("expectancy_ci95") else str(m.get("expectancy"))
        lines.append(f"| {name} | {s['trades']} | {s['win_rate']:.3f} | {s['profit_factor']} | {s['expectancy']} | {s['net_pnl']} | {s['max_drawdown']} | "
                     f"{s['target_hit_rate']:.3f} | {ci(e['development'])} | {e['validation'].get('expectancy')} | {ci(e['holdout'])} | {r['verdict']} |")
    lines += ["", "## Net P&L by year ($ per 2-contract position)", "", "| Strategy | " + " | ".join(str(y) for y in range(2010, 2027)) + " |",
              "|---|" + "---|" * 17]
    for name, r in report["results"].items():
        lines.append(f"| {name} | " + " | ".join(str(round(r["by_year"].get(str(y), {}).get("net_pnl", 0))) for y in range(2010, 2027)) + " |")
    lines += ["", "## Slippage stress (expectancy $)", "", "| Strategy | 0.5 tick | 1 tick | 2 ticks |", "|---|---|---|---|"]
    for name, r in report["results"].items():
        ss = r["slippage_stress"]
        lines.append(f"| {name} | {ss.get('0.5', {}).get('expectancy')} | {ss.get('1.0', {}).get('expectancy')} | {ss.get('2.0', {}).get('expectancy')} |")
    (ROOT / "reports/phase4_backtests.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
