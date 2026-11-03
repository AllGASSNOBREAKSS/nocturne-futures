from dataclasses import replace
from nocturne.ml.promotion import PromotionEvidence, assess_promotion


def evidence():
    return PromotionEvidence("binary", ("2h",), True, True, True, True, True, "prior-tested-model",
                              -.01, .03, .6, True)


def test_good_metrics_cannot_override_missing_independent_history():
    result = assess_promotion(replace(evidence(), independent_holdout=False))
    assert result["decision"] == "NO_PROMOTION"
    assert "INDEPENDENT_HOLDOUT_MISSING" in result["reasons"]


def test_missing_nan_or_failed_metrics_fail_closed_and_pass_is_not_activation():
    for field, value in (("ece", float("nan")), ("auc", .54), ("brier_delta_upper", None)):
        assert assess_promotion(replace(evidence(), **{field: value}))["decision"] == "NO_PROMOTION"
    result = assess_promotion(evidence())
    assert result["decision"] == "ELIGIBLE_FOR_REVIEW"
    assert not result["automatic_activation"]
