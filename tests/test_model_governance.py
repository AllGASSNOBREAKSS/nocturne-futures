import pytest

from nocturne.ml.status import MODELS, VALIDATION_STATUSES, governance


def test_governance_never_enables_trading():
    report = governance()
    assert report["trading_enabled_models"] == []
    assert report["default_trading_decision"] == "NO_TRADE"
    assert all(model["trading_enabled"] is False for model in report["models"])


def test_every_model_declares_status_horizon_and_evidence():
    for model in MODELS:
        assert model["validation_status"] in VALIDATION_STATUSES
        assert model["horizons"], model["model_id"]
        assert model["evidence"], model["model_id"]
        assert model["data_requirement"], model["model_id"]


def test_only_the_range_model_is_shadow_active():
    active = [model["model_id"] for model in MODELS if model["shadow_active"]]
    assert active == ["ndx-range-v1"]
    range_model = next(model for model in MODELS if model["model_id"] == "ndx-range-v1")
    assert range_model["validation_status"] == "RESEARCH_VALIDATED_PENDING_SHADOW"


def test_registry_rejects_a_model_that_enables_trading(monkeypatch):
    import nocturne.ml.status as status
    broken = ({**status.MODELS[0], "trading_enabled": True},)
    monkeypatch.setattr(status, "MODELS", broken)
    with pytest.raises(ValueError, match="trading must not be enabled"):
        status.governance()
