"""Render the shadow monitoring report from durable stores."""
import json
from pathlib import Path

from nocturne.shadow import ShadowStore, evaluation_summary

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/shadow/ndx_range"


def main():
    store = ShadowStore(STORE)
    summary = evaluation_summary(store)
    forecasts = store.forecasts()
    outcomes = store.outcomes()
    report = {
        "model_id": "ndx-range-v1",
        "scope": "NDX cash-session range quantiles; not NQ futures; not a trading signal",
        "status": "SHADOW_ACTIVE" if forecasts else "NOT_STARTED",
        "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
        "trading_decision": "NO_TRADE",
        "forward_predictions": len(forecasts),
        "matured_outcomes": len(outcomes),
        "pending": max(0, len(forecasts) - len(outcomes)),
        "first_forecast": forecasts[0]["target_date"] if forecasts else None,
        "latest_forecast": forecasts[-1]["target_date"] if forecasts else None,
        "evaluation": summary,
        "quality_failures": store.quality_events()[-20:],
        "claim_boundary": ("forward accuracy is not claimed until enough new forecasts "
                           "have matured; historical holdout results are separate"),
    }
    destination = ROOT / "reports/phase3h_shadow_report.json"
    destination.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "forward_predictions",
                                             "matured_outcomes", "pending")}))


if __name__ == "__main__":
    main()
