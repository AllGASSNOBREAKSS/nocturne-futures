"""Phase 3G promotion decisions, including the range-model holdout result."""
import json
from pathlib import Path

from nocturne.ml.promotion import PromotionEvidence, assess_promotion

ROOT = Path(__file__).resolve().parents[1]


def main():
    direction = json.loads((ROOT / "reports/phase3g_daily_direction.json").read_text())
    analogues = json.loads((ROOT / "reports/phase3g_analogues.json").read_text())
    rng = json.loads((ROOT / "reports/phase3g_daily_range.json").read_text())
    survival = json.loads((ROOT / "reports/phase3f_survival.json").read_text())
    decisions = {}

    for name, entry in direction["variants"].items():
        decisions[f"daily_direction_{name}"] = assess_promotion(PromotionEvidence(
            task="binary", horizons=("next_session",), independent_holdout=False,
            sample_adequacy_audited=True, point_in_time_provenance=False,
            calibration_separate=True, regime_stability_audited=True,
            rollback_reference=None, brier_delta_upper=entry["brier_delta"]["high"],
            ece=None, auc=entry["model"]["auc"], class_quality_audited=True))

    for name, entry in analogues["variants"].items():
        decisions[f"analogue_{name}"] = assess_promotion(PromotionEvidence(
            task="binary", horizons=("next_session",), independent_holdout=False,
            sample_adequacy_audited=True, point_in_time_provenance=False,
            calibration_separate=True, regime_stability_audited=False,
            rollback_reference=None, brier_delta_upper=None,
            ece=None, auc=entry["analogue"]["auc"], class_quality_audited=False))

    for name, entry in survival.get("validation", {}).items():
        if not isinstance(entry, dict) or "brier" not in entry:
            continue
        decisions[f"target_survival_{name}"] = assess_promotion(PromotionEvidence(
            task="binary", horizons=("24_5m_bars",), independent_holdout=False,
            sample_adequacy_audited=False, point_in_time_provenance=False,
            calibration_separate=True, regime_stability_audited=False,
            rollback_reference=None,
            brier_delta_upper=(entry.get("paired_delta_vs_frequency") or {}).get("high"),
            ece=entry.get("target_first", {}).get("ece"),
            auc=entry.get("target_first", {}).get("auc"), class_quality_audited=False))

    final = rng.get("final_holdout")
    if final:
        quantiles = final["quantiles"]
        decisions["ndx_daily_range_quantiles"] = {
            "decision": "RESEARCH_VALIDATED_PENDING_SHADOW",
            "scope": "Nasdaq-100 cash-session daily range only; not NQ futures",
            "independent_holdout": {"first": final["test_first"], "last": final["test_last"],
                                    "rows": final["test_rows"], "used_once": True},
            "coverage": {q: round(v["coverage"], 4) for q, v in quantiles.items()},
            "pinball_improved": all(v["pinball_loss"] < v["baseline_loss"] for v in quantiles.values()),
            "reasons_not_promoted": ["requires shadow evaluation on live timestamps",
                                     "index range is not a tradable futures range",
                                     "no futures-specific contract data",
                                     "interval across only three holdout years is unreliable"],
            "automatic_activation": False,
        }
        expansion = final["expansion"]
        decisions["ndx_daily_expansion_classifier"] = {
            "decision": "NO_PROMOTION",
            "scope": "Nasdaq-100 cash-session range expansion > 1.2 ATR",
            "auc": round(expansion["auc"], 4), "ece": expansion["ece"],
            "brier": expansion["brier"], "baseline_brier": expansion["baseline_brier"],
            "recall": expansion["recall"], "precision": expansion["precision"],
            "reasons_not_promoted": ["recall 0.08 makes it unusable as a decision rule",
                                     "shadow evaluation required",
                                     "index range is not a tradable futures range"],
            "automatic_activation": False,
        }

    (ROOT / "reports/phase3g_promotion.json").write_text(json.dumps(decisions, indent=2) + "\n")
    counts = {}
    for value in decisions.values():
        counts[value["decision"]] = counts.get(value["decision"], 0) + 1
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
