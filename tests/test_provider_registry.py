from nocturne.adapters.registry import PROVIDERS, registry, status


def test_registry_never_exposes_credential_values(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "super-secret-value")
    report = registry()
    assert "super-secret-value" not in str(report)
    fred = next(item for item in report["providers"] if item["name"] == "fred")
    assert fred["credential_present"] is True
    assert fred["status"] == "AVAILABLE"


def test_licensed_provider_without_key_is_blocked(monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    databento = next(item for item in PROVIDERS if item.name == "databento")
    assert status(databento) == "BLOCKED"


def test_unimplemented_provider_is_not_available():
    bloomberg = next(item for item in PROVIDERS if item.name == "bloomberg_blpapi")
    assert status(bloomberg) == "NOT_IMPLEMENTED"
    assert bloomberg.access == "LICENSED"
