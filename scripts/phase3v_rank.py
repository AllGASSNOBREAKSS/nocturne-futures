"""Rank Phase 3V candidate signals on independent evidence (no confidence scores).

Inputs: reports/phase3v_research.json (NQ target-before-stop cells) and
reports/phase3v_strategies.json. Expectancy is normalised to points per single
contract. Rank key: holdout expectancy 95% CI lower bound, then development
lower bound, then sample size. A signal is accepted only if both development
and holdout lower bounds are above zero with >= 100 trades each; everything
else is rejected with a stated reason. NO_TRADE regardless of rank.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POINT_VALUE = {"NQ": 20.0, "ES": 50.0}
CONTRACTS = 2  # strategy position size in phase3v_strategies.py


def reason(dev, hold, n_dev, n_hold):
    if n_dev < 100 or n_hold < 100:
        return "INSUFFICIENT_SAMPLE"
    if dev[0] <= 0:
        return "DEVELOPMENT_CI_INCLUDES_ZERO_OR_NEGATIVE"
    if hold[0] <= 0:
        return "HOLDOUT_CI_INCLUDES_ZERO_OR_NEGATIVE"
    return None


def main():
    research = json.loads((ROOT / "reports/phase3v_research.json").read_text())
    strategies = json.loads((ROOT / "reports/phase3v_strategies.json").read_text())
    rows = []
    for cell in research["roots"]["NQ"]["target_before_stop"]["summary"]:
        d, h = cell["development"], cell["holdout"]
        rows.append({"signal": f"NQ fixed-geometry {cell['side']} T{cell['target']}/S{cell['stop']} {cell['horizon_bars']}h from 15:00 UTC open",
                     "family": "target_before_stop", "unit": "points/contract",
                     "conditions": "any day outside roll windows; hourly path, fine-bar tie resolution",
                     "levels": {"target_points": cell["target"], "stop_points": cell["stop"]},
                     "development": {"n": d["n"], "target_first": d["target_first"], "ev": d["net_ev_points"], "ev_ci95": d["net_ev_ci95"]},
                     "holdout": {"n": h["n"], "target_first": h["target_first"], "ev": h["net_ev_points"], "ev_ci95": h["net_ev_ci95"]},
                     "regime_target_first": {"development": d["by_vix"], "holdout": h["by_vix"]}})
    for root, entry in strategies["roots"].items():
        scale = POINT_VALUE[root] * CONTRACTS
        for name, s in entry["strategies"].items():
            b = s["by_slippage_ticks"]["1.0"]
            convert = lambda era: {"n": b[era].get("trades", 0), "win_rate": b[era].get("win_rate"),
                                   "ev": round(b[era]["expectancy"] / scale, 3) if b[era].get("trades") else None,
                                   "ev_ci95": [round(x / scale, 3) for x in b[era]["expectancy_ci95"]] if b[era].get("expectancy_ci95") else None,
                                   "profit_factor": b[era].get("profit_factor")}
            slip = {k: v["all"].get("expectancy") for k, v in s["by_slippage_ticks"].items()}
            rows.append({"signal": f"{root} {name} (existing strategy, 5m)", "family": "strategy", "unit": "points/contract",
                         "conditions": "RTH, existing rule parameters, 1 tick slippage", "levels": "rule-defined per signal",
                         "development": convert("development"), "validation": convert("validation"), "holdout": convert("holdout"),
                         "slippage_sensitivity_dollars_per_position": slip,
                         "intrabar_ordering_1m": s["intrabar_ordering_1m"]})
    for row in rows:
        d, h = row["development"], row["holdout"]
        dev_ci, hold_ci = d.get("ev_ci95") or [float("-inf")] * 2, h.get("ev_ci95") or [float("-inf")] * 2
        why = reason(dev_ci, hold_ci, d["n"], h["n"])
        row["validation_status"] = "ACCEPTED_FOR_SHADOW_RESEARCH" if why is None else "REJECTED"
        row["rejection_reason"] = why
        row["rank_key"] = [hold_ci[0], dev_ci[0], h["n"]]
        row["trading_decision"] = "NO_TRADE"
    rows.sort(key=lambda r: r["rank_key"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "method": __doc__.strip(),
              "accepted": sum(r["validation_status"] != "REJECTED" for r in rows), "candidates": len(rows), "ranking": rows,
              "note": "Ranking orders weak evidence; it is not a recommendation. No signal passed independent evaluation."}
    if report["accepted"]:
        report["note"] = "Accepted signals are research-only shadow candidates, not trading authorisation."
    (ROOT / "reports/phase3v_signal_ranking.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(report["accepted"], "accepted of", len(rows))
    for r in rows[:6]:
        print(r["rank"], r["signal"], r["holdout"]["n"], r["holdout"]["ev"], r["holdout"]["ev_ci95"], r["rejection_reason"])


if __name__ == "__main__":
    main()
