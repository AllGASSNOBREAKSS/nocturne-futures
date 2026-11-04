"""Forward-test report with explicit sample-size limits."""
import json
import hashlib
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
import pandas as pd

from nocturne.shadow import ShadowStore, audit_forecasts, evaluation_summary, health
from nocturne.adapters.yahoo_history import load_history

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/shadow/ndx_range"


def main():
    store = ShadowStore(STORE)
    forecasts = store.forecasts()
    outcomes = store.outcomes()
    summary = evaluation_summary(store)
    state = health(store, datetime.now(timezone.utc))
    try:
        index = load_history(ROOT / "data/shadow/market", "^NDX")
    except FileNotFoundError:
        index = load_history(ROOT / "data/history/yahoo_daily", "^NDX")
    audit = audit_forecasts(store, index, snapshot_root=ROOT / "data/shadow/market/snapshots")
    logs = store.log_events()
    cycles = [event for event in logs if event["event"] in {"CYCLE_OK", "CYCLE_FAILED", "CYCLE_EXCEPTION", "CYCLE_AUDIT_FAILED"}]
    failed_cycles = [event for event in cycles if event["event"] != "CYCLE_OK"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_id": "ndx-range-v1",
        "scope": "NDX cash-session range quantiles; not NQ futures; not a trading signal",
        "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
        "trading_decision": "NO_TRADE",
        "issued": len(forecasts),
        "matured": len(outcomes),
        "pending": max(0, len(forecasts) - len(outcomes)),
        "missed": len(store.missed()),
        "failed": sum(1 for item in audit["failed"]),
        "data_quality_incidents": dict(Counter(event["reason"] for event in store.quality_events())),
        "cycle_availability": {"attempts_logged": len(cycles), "failed_cycles": len(failed_cycles),
                               "failure_fraction": len(failed_cycles) / len(cycles) if cycles else None,
                               "note": "observed local cycles, not service uptime"},
        "issuance_timing": [{"forecast_id": f["forecast_id"],
                             "lead_seconds": (pd.Timestamp(f["session_open_utc"]) - pd.Timestamp(f["created_at"])).total_seconds(),
                             "prediction_compute_seconds": f.get("prediction_compute_seconds")}
                            for f in forecasts],
        "audit": audit,
        "forecast_integrity": {
            "journal_sha256": hashlib.sha256(store.forecast_path.read_bytes()).hexdigest() if forecasts else None,
            "originals": [{"forecast_id": f["forecast_id"], "created_at": f["created_at"],
                           "feature_digest": f["feature_digest"],
                           "inference_revision": f.get("inference_revision", "legacy-unadjusted"),
                           "calibration_warning": None if f.get("inference_revision") else "Frozen residual adjustments were omitted at issuance; evaluate as issued, separately."}
                          for f in forecasts]},
        "health": state,
        "evaluation": summary,
        "claim": ("insufficient forward observations; descriptive only"
                  if len(outcomes) < 30 else "developing forward sample; not a validation claim"),
        "next_milestone": next((f"{n} matured forecasts" for n in (30, 60, 90)
                                if len(outcomes) < n), "monitoring"),
    }
    (ROOT / "reports/phase3i_forward.json").write_text(json.dumps(report, indent=2, default=str) + "\n")

    lines = [
        "# Forward shadow report",
        "",
        f"Model `ndx-range-v1` - status `RESEARCH_VALIDATED_PENDING_SHADOW` - decision `NO_TRADE`",
        "",
        f"- Issued: **{len(forecasts)}**",
        f"- Matured: **{len(outcomes)}**",
        f"- Pending: **{report['pending']}**",
        f"- Missed sessions: **{report['missed']}**",
        f"- Audit failures: **{report['failed']}**",
        "",
    ]
    if not outcomes:
        lines += ["No forward forecast has matured. Coverage, pinball loss and drift are "
                  "intentionally omitted rather than estimated from zero observations.", ""]
    else:
        lines += ["| Quantile | Coverage | 95% interval | Mean pinball | Baseline pinball |",
                  "|---|---:|---|---:|---:|"]
        for name in ("p50", "p80", "p90"):
            interval = summary["coverage_interval"][name]
            lines.append(f"| {name} | {summary['coverage'][name]:.3f} | "
                         f"[{interval['low']:.3f}, {interval['high']:.3f}] | "
                         f"{summary['mean_pinball'][name]:.6f} | "
                         f"{summary['baseline_pinball'].get(name) or float('nan'):.6f} |")
        lines += ["", f"Milestones: {summary['milestones']}", ""]
    lines += ["This report separates implementation from statistical success. "
              "A running service is not evidence of accuracy.", "",
              "Legacy forecasts without an inference revision omitted frozen residual adjustments. "
              "They remain immutable and are scored as issued, separately from corrected inference.", ""]
    (ROOT / "reports/phase3i_forward.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("issued", "matured", "pending", "missed", "failed")}))


if __name__ == "__main__":
    main()
