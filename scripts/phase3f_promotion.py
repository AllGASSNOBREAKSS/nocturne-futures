"""Phase 3F promotion evidence assembled from committed research reports."""
import json
from pathlib import Path

from nocturne.ml.promotion import PromotionEvidence, assess_promotion

ROOT = Path(__file__).resolve().parents[1]


def main():
    direction = json.loads((ROOT / "reports/phase3f_direction.json").read_text())
    survival = json.loads((ROOT / "reports/phase3f_survival.json").read_text())
    quantiles = json.loads((ROOT / "reports/phase3f_quantiles.json").read_text())
    decisions = {}
    for instrument, entry in direction["instruments"].items():
        for name, metrics in entry["models"].items():
            if not isinstance(metrics, dict) or "brier" not in metrics:
                continue
            decisions[f"{instrument}_direction_{name}"] = assess_promotion(PromotionEvidence(
                task="multiclass", horizons=("two_contiguous_future_hours",),
                independent_holdout=False, sample_adequacy_audited=False,
                point_in_time_provenance=False, calibration_separate=True,
                regime_stability_audited=False, rollback_reference=None,
                brier_delta_upper=None, ece=metrics.get("ece"),
                class_quality_audited=False))
    for name, metrics in survival.get("validation", {}).items():
        if not isinstance(metrics, dict) or "brier" not in metrics:
            continue
        decisions[f"NQ_target_survival_{name}"] = assess_promotion(PromotionEvidence(
            task="binary", horizons=("24_5m_bars",), independent_holdout=False,
            sample_adequacy_audited=False, point_in_time_provenance=False,
            calibration_separate=True, regime_stability_audited=False,
            rollback_reference=None,
            brier_delta_upper=(metrics.get("paired_delta_vs_frequency") or {}).get("high"),
            ece=metrics.get("target_first", {}).get("ece"),
            auc=metrics.get("target_first", {}).get("auc"),
            class_quality_audited=False))
    for instrument, entry in quantiles["instruments"].items():
        for name, metrics in entry["summary"].items():
            if not name.startswith("rolling"):
                continue
            decisions[f"{instrument}_range_{name}"] = assess_promotion(PromotionEvidence(
                task="binary", horizons=("two_contiguous_future_hours",),
                independent_holdout=False, sample_adequacy_audited=False,
                point_in_time_provenance=False, calibration_separate=True,
                regime_stability_audited=False, rollback_reference=None,
                brier_delta_upper=metrics["paired_loss_interval"]["high"],
                ece=None, auc=None, class_quality_audited=False))
    (ROOT / "reports/phase3f_promotion.json").write_text(json.dumps(decisions, indent=2) + "\n")
    counts = {}
    for value in decisions.values():
        counts[value["decision"]] = counts.get(value["decision"], 0) + 1
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
