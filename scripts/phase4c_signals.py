"""Phase 4C signal intelligence from stored trade ledgers (no re-simulation).

1. Large-move capture: on NQ sessions whose range reached >=100/200/350/500
   points, how much of the move did each strategy's actual trades capture?
2. Evidence ranking over every tested strategy / setup / ML filter, ordered by
   holdout expectancy lower bound, then development lower bound, then sample.
Win rates and points are recomputed from the trade ledgers themselves.
Writes reports/phase4c_signals.json/.md.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.studio import ROOT, jobs, market

LEDGERS = ROOT / "data/studio/phase4_backtests"
ERAS = {"development": ("2010-01-01", "2019-01-01"), "validation": ("2019-01-01", "2023-01-01"), "holdout": ("2023-01-01", "2027-01-01")}
POINT_VALUE = {"NQ": 20.0, "ES": 50.0}


def era_stats(trades, unit):
    out = {}
    t = pd.to_datetime(trades.entry_time, utc=True)
    for era, (a, b) in ERAS.items():
        f = trades[(t >= pd.Timestamp(a, tz="UTC")) & (t < pd.Timestamp(b, tz="UTC"))]
        net = f.net.to_numpy() / unit
        se = net.std(ddof=1) / np.sqrt(len(net)) if len(net) > 1 else np.nan
        out[era] = {"n": int(len(f)), "win_rate": round(float((f.net > 0).mean()), 4) if len(f) else None,
                    "mean_points": round(float(f.points.mean()), 2) if len(f) else None,
                    "ev_points": round(float(net.mean()), 3) if len(f) else None,
                    "ev_ci95": [round(float(net.mean() - 1.96 * se), 3), round(float(net.mean() + 1.96 * se), 3)] if len(f) > 1 else None}
    return out


def main():
    ledgers = {}
    for folder in sorted(LEDGERS.glob("*")):
        if (folder / "trades.csv").exists():
            ledgers[folder.name] = ("phase4_16y", folder.name.split("_")[0], pd.read_csv(folder / "trades.csv"))
    for job in jobs.list_jobs("backtest"):
        if job["state"] == "SUCCEEDED" and (job.get("config") or {}).get("source") == "databento":
            path = jobs.STORE_ROOT / "attempts" / job["job_id"] / str(job["attempts"]) / "trades.csv"
            if path.exists():
                ledgers[f"studio: {job['name']}"] = ("studio_ui", job["config"]["root"], pd.read_csv(path))
    daily, _ = market.bars("NQ", "1d", limit=100000, source="databento")
    day_range = pd.Series((daily.high - daily.low).to_numpy(), index=pd.to_datetime(daily.timestamp).dt.tz_convert("America/New_York").dt.date.astype(str))
    capture = {}
    for name, (_, root, trades) in ledgers.items():
        if root != "NQ" or trades.empty:
            continue
        trades = trades.assign(day=trades.session_date.astype(str))
        trades["day_range"] = trades.day.map(day_range)
        rows = {}
        for n in (100, 200, 350, 500):
            f = trades[trades.day_range >= n]
            rows[f">={n}"] = {"sessions_in_history": int((day_range >= n).sum()), "trades": int(len(f)),
                              "win_rate": round(float((f.net > 0).mean()), 4) if len(f) else None,
                              "mean_points": round(float(f.points.mean()), 2) if len(f) else None,
                              "median_points": round(float(f.points.median()), 2) if len(f) else None,
                              "share_of_day_range_captured": round(float((f.points / f.day_range).mean()), 4) if len(f) else None,
                              "best_points": round(float(f.points.max()), 2) if len(f) else None}
        capture[name] = rows
    ranking = []
    for name, (origin, root, trades) in ledgers.items():
        unit = POINT_VALUE[root] * 2
        if trades.empty:
            continue
        stats = era_stats(trades, unit)
        regime = pd.cut(trades.vix_prior, [0, 15, 25, 1000], labels=["vix<15", "15-25", "vix>25"])
        ranking.append({"signal": name, "origin": origin, "instrument": root, "trades": int(len(trades)),
                        "wins": int((trades.net > 0).sum()), "losses": int((trades.net <= 0).sum()),
                        "win_rate": round(float((trades.net > 0).mean()), 4), "mean_points": round(float(trades.points.mean()), 2),
                        "median_points": round(float(trades.points.median()), 2), "net_usd": round(float(trades.net.sum()), 2),
                        "by_regime_win_rate": {str(k): round(float((g.net > 0).mean()), 4) for k, g in trades.groupby(regime, observed=True)},
                        "eras": stats, "unit": "points per contract (net)"})
    target = json.loads((ROOT / "reports/phase4_target_study.json").read_text())
    for c in target["cells"]:
        ranking.append({"signal": f"NQ fixed {c['side']} T{c['target']}/S{c['stop']} {c['horizon']} from 10:00 ET", "origin": "phase4_target_study",
                        "instrument": "NQ", "trades": sum(c[e]["n"] for e in ERAS), "eras": {e: {"n": c[e]["n"], "win_rate": c[e]["target_first"],
                        "ev_points": c[e]["net_ev_points"], "ev_ci95": c[e]["net_ev_ci95"]} for e in ERAS}, "unit": "points per contract (net)"})
    ml = json.loads((ROOT / "reports/phase4c_ml.json").read_text()) if (ROOT / "reports/phase4c_ml.json").exists() else {"rows": []}
    for r in ml["rows"]:
        if r.get("economics"):
            ec = r["economics"]
            ranking.append({"signal": f"ML-filtered {r['root']} {r['side']} {r['geometry']} ATR ({r['model']})", "origin": "phase4c_ml", "instrument": r["root"],
                            "trades": ec["development"]["model_filtered"]["n"] + ec["holdout"]["model_filtered"]["n"],
                            "eras": {e: {"n": ec[e]["model_filtered"]["n"], "win_rate": ec[e]["model_filtered"]["win_rate"],
                                         "ev_points": ec[e]["model_filtered"]["mean_r"], "ev_ci95": ec[e]["model_filtered"]["ci95"]} for e in ("development", "holdout")},
                            "unit": "R multiples (net)"})
    for row in ranking:
        d, h = row["eras"].get("development", {}), row["eras"].get("holdout", {})
        lo = lambda m: (m.get("ev_ci95") or [float("-inf")])[0]
        if d.get("n", 0) < 100 or h.get("n", 0) < 100:
            row["status"], row["reason"] = "REJECTED", "INSUFFICIENT_INDEPENDENT_SAMPLE"
        elif lo(d) <= 0:
            row["status"], row["reason"] = "REJECTED", "DEVELOPMENT_EV_CI_NOT_POSITIVE"
        elif lo(h) <= 0:
            row["status"], row["reason"] = "REJECTED", "HOLDOUT_EV_CI_NOT_POSITIVE"
        else:
            row["status"], row["reason"] = "CANDIDATE_RESEARCH_ONLY", None
        row["rank_key"] = [lo(h), lo(d), h.get("n", 0)]
    ranking.sort(key=lambda r: r["rank_key"], reverse=True)
    for i, r in enumerate(ranking, 1):
        r["rank"] = i
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": len(ranking),
              "accepted": sum(r["status"] != "REJECTED" for r in ranking), "large_move_capture": capture, "ranking": ranking,
              "note": "Ranks order evidence; they are not recommendations. NO_TRADE.", "trading_decision": "NO_TRADE"}
    (ROOT / "reports/phase4c_signals.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    fmt = lambda x, d=2: "n/a" if x is None else f"{x:.{d}f}"
    lines = ["# Phase 4C — signal intelligence (authentic NQ/ES, 2010–2026)", "", f"{report['candidates']} candidates, {report['accepted']} accepted.", "",
             "## Did any strategy capture large NQ days?", "", "| Strategy | Day range | Sessions | Trades | Win % | Mean pts | Share of range | Best pts |", "|---|---|---|---|---|---|---|---|"]
    for name, rows in capture.items():
        for k, v in rows.items():
            lines.append(f"| {name} | {k} | {v['sessions_in_history']} | {v['trades']} | {fmt(v['win_rate'] and v['win_rate'] * 100, 1)} | {fmt(v['mean_points'])} | "
                         f"{fmt(v['share_of_day_range_captured'] and v['share_of_day_range_captured'] * 100, 1)}% | {fmt(v['best_points'])} |")
    lines += ["", "## Evidence ranking (top 25)", "", "| # | Signal | Origin | Dev n | Dev EV [CI] | Hold n | Hold EV [CI] | Status |", "|---|---|---|---|---|---|---|---|"]
    for r in ranking[:25]:
        d, h = r["eras"].get("development", {}), r["eras"].get("holdout", {})
        ci = lambda m: f"{fmt(m.get('ev_points'), 3)} [{fmt((m.get('ev_ci95') or [None])[0], 3)}, {fmt((m.get('ev_ci95') or [None, None])[1], 3)}]"
        lines.append(f"| {r['rank']} | {r['signal']} | {r['origin']} | {d.get('n')} | {ci(d)} | {h.get('n')} | {ci(h)} | {r['status']} ({r['reason'] or 'ok'}) |")
    (ROOT / "reports/phase4c_signals.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report["candidates"], "candidates;", report["accepted"], "accepted")


if __name__ == "__main__":
    main()
