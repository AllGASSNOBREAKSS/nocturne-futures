"""Fail-closed evidence checklist; passing permits review, never deployment.

Retains existing binary AUC >= .55, ECE <= .05, baseline improvement and
adequate-independent-sample requirements. Sample adequacy must be audited for
the event/horizon; raw correlated row counts cannot establish independence.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionEvidence:
    task: str
    horizons: tuple[str, ...]
    independent_holdout: bool
    sample_adequacy_audited: bool
    point_in_time_provenance: bool
    calibration_separate: bool
    regime_stability_audited: bool
    rollback_reference: str | None
    brier_delta_upper: float | None
    ece: float | None
    auc: float | None = None
    class_quality_audited: bool = False


def assess_promotion(evidence):
    reasons = []
    for name in ("independent_holdout", "sample_adequacy_audited", "point_in_time_provenance",
                 "calibration_separate", "regime_stability_audited", "class_quality_audited"):
        if not getattr(evidence, name):
            reasons.append(name.upper() + "_MISSING")
    if evidence.task not in {"binary", "multiclass"}:
        reasons.append("UNSUPPORTED_TASK")
    if not evidence.horizons:
        reasons.append("SUPPORTED_HORIZONS_MISSING")
    if not evidence.rollback_reference:
        reasons.append("ROLLBACK_REFERENCE_MISSING")
    finite = lambda x: x is not None and math.isfinite(x)
    if not finite(evidence.brier_delta_upper) or evidence.brier_delta_upper >= 0:
        reasons.append("BASELINE_IMPROVEMENT_UNCERTAIN")
    if not finite(evidence.ece) or not 0 <= evidence.ece <= .05:
        reasons.append("CALIBRATION_GATE_FAILED")
    if evidence.task == "binary" and (not finite(evidence.auc) or not .55 <= evidence.auc <= 1):
        reasons.append("AUC_GATE_FAILED")
    return {"decision": "NO_PROMOTION" if reasons else "ELIGIBLE_FOR_REVIEW", "reasons": reasons,
            "automatic_activation": False, "supported_horizons": list(evidence.horizons)}
