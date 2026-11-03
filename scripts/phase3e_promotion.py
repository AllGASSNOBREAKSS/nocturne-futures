import json
from pathlib import Path
from nocturne.ml.promotion import PromotionEvidence, assess_promotion

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = json.loads((ROOT / "reports/phase3e_ablation.json").read_text())
    decisions = {}
    for name, experiment in report["experiments"].items():
        for model, result in experiment["summary"].items():
            if not model.endswith("without_none"):
                continue
            metrics = result["metrics"]
            evidence = PromotionEvidence(task="multiclass" if "direction" in name else "binary",
                horizons=("two_contiguous_future_hours",), independent_holdout=False,
                sample_adequacy_audited=False, point_in_time_provenance=False,
                calibration_separate=True, regime_stability_audited=False,
                rollback_reference=None, brier_delta_upper=result["delta_frequency"]["high"],
                ece=metrics["ece"], auc=metrics.get("auc"), class_quality_audited=False)
            decisions[f"{name}_{model}"] = assess_promotion(evidence)
    (ROOT / "reports/phase3e_promotion.json").write_text(json.dumps(decisions, indent=2) + "\n")
    print(json.dumps({k: v["decision"] for k, v in decisions.items()}))


if __name__ == "__main__":
    main()
