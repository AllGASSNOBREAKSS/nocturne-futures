"""Run the Phase 3V zero-cost futures research (Yahoo NQ=F/ES=F + free PIT features).

Writes reports/phase3v_research.json and .md, plus target-before-stop
records under data/studies/phase3v/. Retrospective walk-forward only; this is
not live or forward-tested evidence.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nocturne.collector.store import Archive
from nocturne.research import futures_free as ff
from nocturne.research.free_data_experiment import FREE

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = {"NQ": [100, 200, 350, 500], "ES": [25, 50, 100, 150]}


def main():
    archive = Archive(ROOT / "data/history/free")
    vix = archive.load("fred", "VIXCLS")
    vix_by_date = pd.Series(vix.value.to_numpy(), index=pd.to_datetime(vix.date)).sort_index()
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "protocol": ff.PROTOCOL, "families": ff.FAMILIES,
              "scope": "RETROSPECTIVE_WALK_FORWARD_CONTINUOUS_PROXY_NOT_RAW_CONTRACTS_NOT_FORWARD_TEST",
              "roots": {}, "spend_usd": 0}
    for root, symbol in (("NQ", "NQ.v.0"), ("ES", "ES.v.0")):
        rolls = load_rolls(symbol)
        ff.PROTOCOL["large_move_points"] = THRESHOLDS[root]
        data, audit, near = ff.daily_frame(archive, root, rolls)
        tasks = {"direction_next_settle_up": ("next_up", "base_up"), "compression_next_range_lt_0.6atr": ("y_compress", "base_compress")}
        tasks |= {f"range_ge_{n}pts": (f"y_range_{n}", f"base_range_{n}") for n in THRESHOLDS[root]}
        configs = {"price_logit": (ff.PRICE, False), "all_logit": (ff.PRICE + FREE, False), "all_lgbm": (ff.PRICE + FREE, True)}
        configs |= {f"price+{fam}_logit": (ff.PRICE + cols, False) for fam, cols in ff.FAMILIES.items()}
        results = {}
        for task, (label, base) in tasks.items():
            results[task], preds = {}, {}
            for name, (features, lgbm) in configs.items():
                preds[name] = pred = ff.walk_forward(data, label, base, features, lgbm)
                results[task][name] = ff.score(pred) if len(pred) else {"verdict": "NO_PREDICTIONS"}
            # Incremental value of each feature family over price-only, on matched sessions.
            for name, pred in preds.items():
                if name != "price_logit" and len(pred):
                    results[task][name]["increment_vs_price_logit"] = ff.increment(pred, preds["price_logit"])
        entry = {"rolls_from_databento_symbology": len(rolls), "sessions_after_roll_exclusion": len(data),
                 "sessions_excluded_near_roll": near, "first": str(data.date.min()), "last": str(data.date.max()),
                 "pit_audit": audit, "tasks": results, "large_move_frequencies": ff.large_move_table(data)}
        if root == "NQ":
            records = ff.target_before_stop(archive, root, rolls, vix_by_date)
            study = ROOT / "data/studies/phase3v"
            study.mkdir(parents=True, exist_ok=True)
            path = study / "nq_target_before_stop.csv"
            records.to_csv(path, index=False, lineterminator="\n")
            summary, cut = ff.tbs_summary(records)
            entry["target_before_stop"] = {"records": len(records), "sessions": int(records.date.nunique()),
                                           "holdout_starts": cut, "records_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                           "summary": summary}
        report["roots"][root] = entry
    (ROOT / "reports/phase3v_research.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    (ROOT / "reports/phase3v_research.md").write_text(markdown(report), encoding="utf-8")
    for root, entry in report["roots"].items():
        print(root, {t: {c: r["verdict"] for c, r in v.items()} for t, v in entry["tasks"].items()})


ROLLS = ROOT / "data/history/free/rolls/front_month_volume_rolls.json"


def load_rolls(symbol):
    """Derived roll dates (no raw provider payload) so fresh clones can reproduce."""
    metadata = ROOT / "data/licensed/databento/metadata"
    stored = json.loads(ROLLS.read_text()) if ROLLS.exists() else {}
    if (metadata / "objects").exists():
        dates = [str(d) for d in ff.roll_dates(ROOT / "reports/phase3v_preflight.json", metadata, symbol)]
        receipt = next(r for r in json.loads((ROOT / "reports/phase3v_preflight.json").read_text())["metadata_receipts"]
                       if r["method"] == "symbology.resolve")
        if stored.get(symbol, {}).get("dates") not in (None, dates):
            raise ValueError("derived roll calendar disagrees with the verified symbology receipt")
        stored[symbol] = {"dates": dates, "source": "Databento GLBX.MDP3 symbology.resolve (free metadata), continuous volume roll",
                          "receipt_sha256": receipt["body_sha256"]}
        ROLLS.parent.mkdir(parents=True, exist_ok=True)
        ROLLS.write_text(json.dumps(stored, indent=2) + "\n")
    return sorted(pd.Timestamp(d).date() for d in stored[symbol]["dates"])


def f(x, d=4):
    return "n/a" if x is None else f"{x:.{d}f}"


def markdown(report):
    lines = ["# Phase 3V — zero-cost futures research (Yahoo NQ=F / ES=F)", "",
             f"Generated {report['generated_at']}. Spend: **$0**. Scope: retrospective walk-forward on continuous "
             "front-month proxies; not raw contracts, not order flow, not forward evidence. NO_PROMOTION / NO_TRADE.", ""]
    for root, entry in report["roots"].items():
        lines += [f"## {root}", "", f"Sessions {entry['first']} → {entry['last']}: {entry['sessions_after_roll_exclusion']} usable after "
                  f"excluding {entry['sessions_excluded_near_roll']} near {entry['rolls_from_databento_symbology']} Databento volume rolls.", "",
                  "| Task | Config | Dev n | Dev Brier model | Dev Brier baseline | Dev Δ [95% CI] | Dev AUC | Holdout Δ | Holdout AUC | Verdict |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for task, configs in entry["tasks"].items():
            for name, r in configs.items():
                d, h = r.get("development", {}), r.get("holdout", {})
                if "model" not in d:
                    lines.append(f"| {task} | {name} | {d.get('n', 0)} | | | | | | | {r['verdict']} |")
                    continue
                dd, hd = d["brier_model_minus_baseline"], h.get("brier_model_minus_baseline", {})
                lines.append(f"| {task} | {name} | {d['model']['n']} | {f(d['model']['brier'], 5)} | {f(d['trailing_baseline']['brier'], 5)} | "
                             f"{dd['mean']:+.5f} [{dd['ci95'][0]:+.5f}, {dd['ci95'][1]:+.5f}] | {f(d['model']['auc'])} | "
                             f"{hd.get('mean', float('nan')):+.5f} | {f(h.get('model', {}).get('auc'))} | {r['verdict']} |")
        lines += ["", "### Feature-family increment over price-only logistic (Brier Δ, matched sessions; negative = family helps)", "",
                  "| Task | Config | Dev n | Dev Δ [95% CI] | Holdout n | Holdout Δ [95% CI] | Verdict |", "|---|---|---|---|---|---|---|"]
        for task, configs in entry["tasks"].items():
            for name, r in configs.items():
                inc = r.get("increment_vs_price_logit")
                if not inc:
                    continue
                d, h = inc["development"], inc["holdout"]
                lines.append(f"| {task} | {name} | {d['n']} | {d['mean']:+.5f} [{d['ci95'][0]:+.5f}, {d['ci95'][1]:+.5f}] | {h['n']} | "
                             f"{h['mean']:+.5f} [{h['ci95'][0]:+.5f}, {h['ci95'][1]:+.5f}] | {inc['verdict']} |")
        lines += ["", "### Next-session large-move frequencies (Wilson 95% CI)", "",
                  "| Era / VIX regime | Sessions | Median range | " + " | ".join(f"range≥{n}" for n in THRESHOLDS[root]) + " |",
                  "|---|---|---|" + "---|" * len(THRESHOLDS[root])]
        for cell, v in entry["large_move_frequencies"].items():
            parts = [f"{v[f'range_ge_{n}']['p']} [{v[f'range_ge_{n}']['ci95'][0]}, {v[f'range_ge_{n}']['ci95'][1]}]" if v["sessions"] else "—"
                     for n in THRESHOLDS[root]]
            lines.append(f"| {cell} | {v['sessions']} | {f(v['median_range_pts'], 1)} | " + " | ".join(parts) + " |")
        if "target_before_stop" in entry:
            t = entry["target_before_stop"]
            lines += ["", f"### NQ target-before-stop (hourly, {t['sessions']} sessions, holdout from {t['holdout_starts']})", "",
                      "Entry at the 15:00 UTC hourly open; same-bar touches resolved with 1m/5m bars when available, otherwise STOP_FIRST. "
                      "Net = 0.75 points round-trip cost.", "",
                      "| Horizon | Target/Stop | Side | Dev n | Dev target-first | Dev EV [CI] | Hold n | Hold target-first | Hold EV [CI] | Ambiguous→stop | Status |",
                      "|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in t["summary"]:
                d, h = r["development"], r["holdout"]
                lines.append(f"| {r['horizon_bars']}h | {r['target']}/{r['stop']} | {r['side']} | {d['n']} | {d['target_first']['p']} | "
                             f"{d['net_ev_points']} {d['net_ev_ci95']} | {h['n']} | {h['target_first']['p']} | {h['net_ev_points']} {h['net_ev_ci95']} | "
                             f"{d['ambiguous_conservative'] + h['ambiguous_conservative']} | {r['status']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
