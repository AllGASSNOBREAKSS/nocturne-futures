"""Phase 4C pre-registered ML sweep on authentic Databento sessions.

Submits every experiment through the desktop app's job store (studio.jobs) and
executes it with the same orchestrator worker the app uses, so each result is
inspectable in ML Model Studio. Test years 2012-2026; holdout from 2023
(2023-2026 was inspected by Phase 4 strategy backtests, so it is a reused, not
untouched, holdout). Fixed hyperparameters; nothing is tuned on results.
Writes reports/phase4c_ml.json and reports/phase4c_ml.md.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from nocturne.research.orchestrator import run_lane
from nocturne.studio import ROOT, dataset, jobs

BASE = {"source": "databento", "first_test_year": 2012, "last_test_year": 2026, "holdout_from": 2023, "embargo_days": 5, "calibration_rows": 250}
MODELS = {"logistic": ["price", "intraday"], "lightgbm": ["price", "intraday", "volatility"]}


def experiments():
    out = []
    for root in ("NQ", "ES"):
        objectives = [{"objective": o} for o in ("direction", "expansion", "compression", "trend_day", "touch_prior_high", "touch_prior_low", "touch_prior_vwap")]
        objectives += [{"objective": "range_ge_points", "threshold_points": n} for n in dataset.POINT_THRESHOLDS[root]]
        objectives += [{"objective": "range_ge_atr", "threshold_atr": k} for k in (1.0, 1.5)]
        objectives += [{"objective": "target_before_stop", "geometry": g, "side": s} for g in dataset.TBS_GEOMETRIES for s in ("long", "short")]
        for o in objectives:
            for model, fams in MODELS.items():
                out.append({**BASE, **o, "root": root, "model": model, "feature_families": fams, "group": "main"})
        out.append({**BASE, "root": root, "objective": "range_quantile", "model": "lightgbm", "feature_families": ["price", "intraday", "volatility"], "group": "main"})
        for objective in ("direction", "expansion"):
            for extra in ([], ["intraday"], ["volatility"], ["rates_credit"], ["positioning"], ["filings"]):
                out.append({**BASE, "root": root, "objective": objective, "model": "logistic", "feature_families": ["price", *extra],
                            "group": "ablation", "family": extra[0] if extra else "price_only"})
    for e in out:
        tag = e["objective"] + {"range_ge_points": f"-{e.get('threshold_points')}", "range_ge_atr": f"-{e.get('threshold_atr')}atr",
                                "target_before_stop": f"-{e.get('side')}-{e.get('geometry')}"}.get(e["objective"], "")
        e["name"] = f"4C {e['group']} {e['root']} {tag} {e['model']}" + (f" +{e['family']}" if e.get("family") else "")
    return out


def main():
    done = {j["name"]: j for j in jobs.list_jobs("training") if j["state"] in ("SUCCEEDED", "FAILED", "BLOCKED")}
    plan = experiments()
    for e in plan:
        if e["name"] not in done:
            r = jobs.submit("training", {k: v for k, v in e.items() if k not in ("group", "family")} | {"name": e["name"]})
            if r["status"] != "QUEUED":
                raise SystemExit(f"rejected {e['name']}: {r}")
    started = time.time()
    while True:
        tick = run_lane(jobs.store(), ROOT, "research", max_jobs=20, budget_seconds=1800, backoff_seconds=5)
        pending = [j for j in jobs.list_jobs("training") if j["state"] in ("QUEUED", "RUNNING", "RETRY_WAIT") and j["name"].startswith("4C ")]
        print(f"{time.time() - started:7.0f}s executed {tick.get('executed')} pending {len(pending)}", flush=True)
        if not pending:
            break
    rows = []
    by_name = {j["name"]: j for j in jobs.list_jobs("training")}
    for e in plan:
        j = jobs.get(by_name[e["name"]]["job_id"])
        rep = j.get("report") or {}
        metrics = rep.get("metrics", {})
        row = {**{k: e.get(k) for k in ("name", "group", "family", "root", "objective", "model", "threshold_points", "threshold_atr", "geometry", "side")},
               "job_id": j["job_id"], "state": j["state"], "verdict": rep.get("verdict"), "sessions": rep.get("sessions_scored"),
               "economics": rep.get("economics"), "feature_importance": (rep.get("feature_importance") or [])[:5]}
        for era in ("development", "holdout"):
            m = metrics.get(era, {})
            if "model" in m and "auc" in m["model"]:
                row[era] = {"n": m["model"]["n"], "auc": m["model"]["auc"], "balanced_accuracy": m["model"]["balanced_accuracy"],
                            "brier": m["model"]["brier"], "log_loss": m["model"]["log_loss"], "baseline_brier": m["baseline"]["brier"],
                            "baseline_auc": m["baseline"]["auc"], "delta": m["brier_model_minus_baseline"]["mean"],
                            "ci95": m["brier_model_minus_baseline"]["ci95"],
                            "max_calibration_gap": max((abs(b["mean_predicted"] - b["observed"]) for b in m.get("reliability", []) if b["n"] >= 30), default=None)}
            elif "model" in m:
                row[era] = {"coverage": {k: v for k, v in m["model"].items() if k.startswith("coverage")}, "pinball": m["model"]["mean_pinball"],
                            "baseline_pinball": m["baseline"]["mean_pinball"], "baseline_coverage": {k: v for k, v in m["baseline"].items() if k.startswith("coverage")},
                            "delta": m["pinball_model_minus_baseline"]["mean"], "ci95": m["pinball_model_minus_baseline"]["ci95"]}
        rows.append(row)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "protocol": BASE, "models": MODELS, "experiments": len(rows),
              "verdicts": {v: sum(r["verdict"] == v for r in rows) for v in ("ACCEPT_RESEARCH_ONLY", "INCONCLUSIVE", "REJECT")},
              "rows": rows, "holdout_note": "2023-2026 previously inspected in Phase 4 strategy backtests: reused holdout, not untouched",
              "trading_decision": "NO_TRADE"}
    (ROOT / "reports/phase4c_ml.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    fmt = lambda x, d=4: "n/a" if x is None else f"{x:.{d}f}"
    lines = ["# Phase 4C — ML research on authentic NQ/ES sessions (Databento 2010–2026)", "",
             f"Generated {report['generated_at']}. {len(rows)} experiments run through the desktop job store. Test years 2012–2026, "
             "holdout 2023–2026 (reused). Brier Δ = model − trailing-frequency baseline (negative is better).", "",
             f"Verdicts: {report['verdicts']}", "", "## Classification objectives", "",
             "| Root | Objective | Model | Dev n | Dev AUC | Dev Brier (base) | Dev Δ [95% CI] | Hold AUC | Hold Δ | Max cal. gap | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        d, h = r.get("development"), r.get("holdout")
        if r["group"] != "main" or not d or "auc" not in d:
            continue
        obj = r["objective"] + (f" {r['threshold_points']}" if r["threshold_points"] else "") + (f" {r['threshold_atr']}×ATR" if r["threshold_atr"] else "") + (f" {r['side']} {r['geometry']}" if r["geometry"] else "")
        lines.append(f"| {r['root']} | {obj} | {r['model']} | {d['n']} | {fmt(d['auc'], 3)} | {fmt(d['brier'])} ({fmt(d['baseline_brier'])}) | "
                     f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] | {fmt(h['auc'] if h else None, 3)} | "
                     f"{(h or {}).get('delta', float('nan')):+.4f} | {fmt(d['max_calibration_gap'], 3)} | {r['verdict']} |")
    lines += ["", "## Range quantiles", ""]
    for r in rows:
        if r["objective"] == "range_quantile" and r.get("development"):
            d, h = r["development"], r.get("holdout") or {}
            lines.append(f"- {r['root']}: dev pinball {fmt(d['pinball'], 2)} vs baseline {fmt(d['baseline_pinball'], 2)}, Δ {d['delta']:+.2f} "
                         f"[{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]; coverage {d['coverage']}; holdout Δ {h.get('delta', float('nan')):+.2f}; {r['verdict']}")
    lines += ["", "## Target-before-stop economics (trade only when p > break-even)", "",
              "| Root | Side | Geometry (ATR) | Model | Dev trades | Dev mean R [CI] | Dev always-trade R | Hold trades | Hold mean R [CI] |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ec = r.get("economics")
        if ec:
            dm, da, hm = ec["development"]["model_filtered"], ec["development"]["always_trade"], ec["holdout"]["model_filtered"]
            ci = lambda m: f"{fmt(m['mean_r'], 3)} [{fmt(m['ci95'][0], 3)}, {fmt(m['ci95'][1], 3)}]" if m.get("ci95") else fmt(m.get("mean_r"), 3)
            lines.append(f"| {r['root']} | {r['side']} | {r['geometry']} | {r['model']} | {dm['n']} | {ci(dm)} | {ci(da)} | {hm['n']} | {ci(hm)} |")
    lines += ["", "## Feature-family ablation (logistic, Brier Δ vs baseline)", "", "| Root | Objective | Features | Dev Δ [CI] | Hold Δ | Verdict |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r["group"] == "ablation" and r.get("development"):
            d, h = r["development"], r.get("holdout") or {}
            lines.append(f"| {r['root']} | {r['objective']} | {r['family']} | {d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] | {h.get('delta', float('nan')):+.4f} | {r['verdict']} |")
    (ROOT / "reports/phase4c_ml.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report["verdicts"])


if __name__ == "__main__":
    main()
