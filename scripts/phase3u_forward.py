"""Read-only Phase 3U forward-test report for the ndx-range-v1 shadow journal.

Never writes forecasts/outcomes. Matured observations are scored against the
issued quantiles and a trailing 250-session empirical baseline computed only
from bars up to each forecast's data date. Two observations are descriptive,
not statistical evidence.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.adapters.yahoo_history import load_history
from nocturne.collector.store import Archive

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "data/shadow/ndx_range"
LEVELS = {"p50": .5, "p80": .8, "p90": .9}


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def pinball(y, q, a):
    d = y - q
    return float(max(a * d, (a - 1) * d))


def main():
    forecasts, outcomes = lines(JOURNAL / "forecasts.jsonl"), {o["forecast_id"]: o for o in lines(JOURNAL / "outcomes.jsonl")}
    bars = load_history(ROOT / "data/shadow/market", "^NDX")
    bars["range"] = (bars.high - bars.low) / bars.close
    archive = Archive(ROOT / "data/history/free")
    vix = archive.load("fred", "VIXCLS").set_index("date").value
    cot = archive.load("cftc", "tff_futures_only")
    fed = archive.load("fed", "press_releases")
    # Quarantine membership comes from the shadow cycle's own status report.
    status = json.loads((ROOT / "reports/phase3h_shadow_status.json").read_text(encoding="utf-8-sig"))
    blocked = set(status.get("quarantined_forecast_ids") or [])
    rows = []
    for f in forecasts:
        history = bars[bars.date.astype(str) <= f["data_date"]].tail(250)
        baseline = {k: float(np.quantile(history["range"], a)) for k, a in LEVELS.items()}
        row = {"forecast_id": f["forecast_id"], "issued_at": f["created_at"], "data_date": f["data_date"],
               "target_date": f["target_date"], "horizon": "next NDX cash session high-low range",
               "model": f"{f['model_id']} {f['model_version']} ({f.get('inference_revision', 'legacy-unadjusted')})",
               "reference_close": f["reference_close"],
               "forecast_fraction": f["quantiles"],
               "forecast_points": {k: round(v * f["reference_close"], 2) for k, v in f["quantiles"].items()},
               "trailing250_baseline_fraction": baseline,
               "context": {"vix_close_on_data_date": float(vix.get(f["data_date"], np.nan)),
                           "baseline_window_last": str(history.date.iloc[-1])}}
        outcome = outcomes.get(f["forecast_id"])
        if outcome:
            y = outcome["realized_range_pct"]
            row |= {"status": "MATURED_VERIFIED", "realized_fraction": y, "realized_points": outcome["realized_range_points"],
                    "covered": {k: y <= v for k, v in f["quantiles"].items()},
                    "pinball_model": {k: pinball(y, f["quantiles"][k], a) for k, a in LEVELS.items()},
                    "pinball_trailing_baseline": {k: pinball(y, baseline[k], a) for k, a in LEVELS.items()},
                    "outcome_source": outcome["source_reliability"]}
            row["mean_pinball"] = {"model": float(np.mean(list(row["pinball_model"].values()))),
                                   "trailing_baseline": float(np.mean(list(row["pinball_trailing_baseline"].values())))}
        else:
            row["status"] = "PENDING_AUDIT_BLOCKED" if f["forecast_id"] in blocked else "PENDING"
            row["evaluation_requirement"] = ("target bar complete after next-day 00:00 UTC bound AND reference-close audit "
                                             "cleared by independent final OHLC evidence; never force-evaluated")
        rows.append(row)
    matured = [r for r in rows if r["status"] == "MATURED_VERIFIED"]
    latest_cot = cot[cot.cftc_contract_market_code.astype(str) == "209742"].sort_values("report_date").iloc[-1]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "model_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
              "counts": {"issued": len(rows), "matured": len(matured), "pending": len(rows) - len(matured),
                         "audit_blocked": sum(r["status"] == "PENDING_AUDIT_BLOCKED" for r in rows), "missed": 0},
              "latest_forecast": rows[-1] if rows else None, "forecasts": rows,
              "aggregate_descriptive_only": {"n": len(matured),
                                             "mean_pinball_model": float(np.mean([r["mean_pinball"]["model"] for r in matured])) if matured else None,
                                             "mean_pinball_trailing_baseline": float(np.mean([r["mean_pinball"]["trailing_baseline"] for r in matured])) if matured else None,
                                             "p80_coverage": float(np.mean([r["covered"]["p80"] for r in matured])) if matured else None,
                                             "note": "n=2; no statistical accuracy claim is possible"},
              "market_context_now": {"latest_cot_nq_report_date": latest_cot.report_date,
                                     "latest_cot_nq_available_at": latest_cot.available_at,
                                     "nq_asset_manager_net_pct_oi": float((latest_cot.asset_mgr_positions_long - latest_cot.asset_mgr_positions_short) / latest_cot.open_interest_all),
                                     "recent_fed_events": fed.sort_values("published_at").tail(5)[["published_at", "event_type", "title"]].to_dict("records")},
              "journal_sha256": {name: hashlib.sha256((JOURNAL / name).read_bytes()).hexdigest() for name in ("forecasts.jsonl", "outcomes.jsonl")},
              "writes_to_journal": False, "trading_decision": "NO_TRADE"}
    (ROOT / "reports/phase3u_forward.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "aggregate": report["aggregate_descriptive_only"]}, default=str))


if __name__ == "__main__":
    main()
