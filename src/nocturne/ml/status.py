"""Single source of truth for model governance and trading eligibility.

Every model declares its validation status, supported horizon and data
requirement. ``trading_enabled`` is false for all research models by design; a
model can only be enabled through a separate, explicit promotion decision.
"""
from __future__ import annotations

VALIDATION_STATUSES = {
    "RESEARCH_ONLY",
    "RESEARCH_VALIDATED_PENDING_SHADOW",
    "SHADOW_ACTIVE",
    "DATA_BLOCKED",
    "VALIDATION_FAILED",
    "NO_PROMOTION",
}

MODELS = (
    {
        "model_id": "ndx-range-v1",
        "kind": "cash_session_range_quantiles",
        "instrument": "^NDX",
        "horizons": ["next_cash_session"],
        "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
        "shadow_active": True,
        "trading_enabled": False,
        "data_requirement": "daily NDX and VIX bars, available next UTC midnight",
        "evidence": "one-shot 2024-2026 holdout: coverage 0.534/0.816/0.920",
        "limitations": ["index range is not a futures range", "forward cohorts must be validated separately; sample size is not a promotion gate by itself",
                        "first forecast omitted residual calibration; score legacy inference separately"],
        "inference_revision": "residual-adjusted-v1",
    },
    {
        "model_id": "ndx-range-expansion-v1",
        "kind": "range_expansion_classifier",
        "instrument": "^NDX",
        "horizons": ["next_cash_session"],
        "validation_status": "NO_PROMOTION",
        "shadow_active": False,
        "trading_enabled": False,
        "data_requirement": "daily NDX and VIX bars",
        "evidence": "holdout AUC 0.7155, ECE 0.0173, recall 0.0846",
        "limitations": ["recall too low for a decision rule"],
    },
    {
        "model_id": "nq-two-hour-direction",
        "kind": "multiclass_direction",
        "instrument": "NQ",
        "horizons": ["two_contiguous_future_hours"],
        "validation_status": "NO_PROMOTION",
        "shadow_active": False,
        "trading_enabled": False,
        "data_requirement": "hourly NQ/ES with VIX context",
        "evidence": "material AUC 0.699; bull-vs-bear AUC 0.534",
        "limitations": ["activity detection, not direction", "no independent holdout"],
    },
    {
        "model_id": "nq-target-survival",
        "kind": "competing_outcome_target_first",
        "instrument": "NQ",
        "horizons": ["24_5m_bars"],
        "validation_status": "NO_PROMOTION",
        "shadow_active": False,
        "trading_enabled": False,
        "data_requirement": "contract-level 5m bars with reliable intrabar sequencing",
        "evidence": "logistic Brier 0.548 vs 0.628; ECE 0.061; interval includes zero",
        "limitations": ["90 signals", "no licensed intraday history",
                        "Phase 3F AJ-v1 censoring defect corrected in 3L; old survival outputs require recomputation, not promotion"],
    },
    {
        "model_id": "nq-session-direction",
        "kind": "multiclass_direction",
        "instrument": "NQ",
        "horizons": ["next_same_session"],
        "validation_status": "NO_PROMOTION",
        "shadow_active": False,
        "trading_enabled": False,
        "data_requirement": "complete analytical sessions",
        "evidence": "86 complete sessions; frequency baseline wins",
        "limitations": ["sample too small", "ASIA windows incomplete"],
    },
)


def governance() -> dict:
    for model in MODELS:
        if model["validation_status"] not in VALIDATION_STATUSES:
            raise ValueError(f"unknown validation status: {model['validation_status']}")
        if model["trading_enabled"]:
            raise ValueError("trading must not be enabled by this registry")
    return {
        "models": [dict(model) for model in MODELS],
        "trading_enabled_models": [m["model_id"] for m in MODELS if m["trading_enabled"]],
        "default_trading_decision": "NO_TRADE",
        "promotion_policy": "fail-closed; review eligibility is not activation",
        "notes": ["validation status is separate from trading eligibility",
                  "shadow results are not trading signals"],
    }
