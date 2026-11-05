"""Synthetic metadata/consumption tests; no account, entitlement or market claims."""
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from nocturne.adapters.databento_access import DatabentoAccess, check_approval, pilot_request
from nocturne.adapters.databento import DatabentoBars, normalize_csv


class MetadataTransport:
    def __init__(self):
        self.calls = []
        self.cost = .01
        self.condition = "available"

    def get(self, url, **kwargs):
        self.calls.append(url)
        method = url.split("/")[-1]
        params = kwargs["params"]
        values = {"metadata.list_datasets": ["GLBX.MDP3"], "metadata.list_schemas": ["ohlcv-1m", "trades", "tbbo", "mbp-1", "mbp-10", "mbo"],
                  "metadata.get_dataset_range": {"range_by_schema": {"ohlcv-1m": {"start": "2020-01-01T00:00Z", "end": "2030-01-01T00:00Z"}}},
                  "metadata.get_cost": self.cost, "metadata.get_record_count": 1, "metadata.get_billable_size": 64}
        if method == "metadata.get_dataset_condition":
            value = [{"date": d.strftime("%Y-%m-%d"), "condition": self.condition}
                     for d in pd.date_range(params["start_date"], params["end_date"], freq="D")]
        else:
            value = values[method]
        return SimpleNamespace(status_code=200, content=json.dumps(value).encode(), json=lambda: value)

    def post(self, url, **kwargs):
        self.calls.append(url)
        p = kwargs["data"]
        value = {"result": {p["symbols"]: [{"s": "123", "d0": p["start_date"], "d1": p["end_date"]}]},
                 "partial": [], "not_found": [], "status": 0}
        return SimpleNamespace(status_code=200, content=json.dumps(value).encode(), json=lambda: value)


def approved_fixture(tmp_path, contract="NQH5", instrument="NQ", start="2025-01-02T00:00Z", end="2025-01-03T00:00Z"):
    transport = MetadataTransport()
    quote = DatabentoAccess(key="fixture-not-a-key", transport=transport).preflight(tmp_path / "metadata", contract=contract,
                 instrument=instrument, start=start, end=end)
    assert quote["status"] == "QUOTED_AWAITING_OPERATOR_APPROVAL", quote
    approval = {"quote_id": quote["quote_id"], "authorized": True, "operator_reference": "synthetic-test-only",
                "approved_at": pd.Timestamp.now(tz="UTC").isoformat(),
                "expires_at": (pd.Timestamp(quote["generated_at"]) + pd.Timedelta("1h")).isoformat(),
                "max_cost_usd": "0.01", "max_billable_bytes": 64}
    return quote, approval


def test_missing_key_makes_no_calls_and_does_not_invent_credit_or_cost(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    transport = MetadataTransport()
    r = DatabentoAccess(transport=transport).preflight(tmp_path, contract="NQZ6", instrument="NQ", start="2026-11-01T23:00Z", end="2026-11-02T22:00Z")
    assert r["status"] == "DATA_BLOCKED" and r["cost_usd"] is None
    assert not transport.calls and not r["time_series_requested"]


def test_metadata_quotes_only_free_endpoints_and_archives_hashes(tmp_path):
    quote, approval = approved_fixture(tmp_path)
    assert quote["resolved_instrument_id"] == 123
    assert quote["billable_bytes"] == 64
    assert not quote["consumption_authorized"]
    for receipt in quote["metadata_receipts"]:
        assert (tmp_path / "metadata/objects" / receipt["body_sha256"]).exists()
    assert "fixture-not-a-key" not in json.dumps(quote)
    check_approval(quote, approval, quote["request"], "NQ")


@pytest.mark.parametrize("change", ["scope", "quote_hash", "expired", "budget", "no_consent"])
def test_changed_request_quote_expiry_and_budget_block_consumption(tmp_path, change):
    quote, approval = approved_fixture(tmp_path)
    request = dict(quote["request"])
    if change == "scope": request["symbols"] = "ESZ6"
    if change == "quote_hash": quote["cost_usd"] = "0"
    if change == "expired": approval["expires_at"] = quote["generated_at"]
    if change == "budget": approval["max_cost_usd"] = "0"
    if change == "no_consent": approval["authorized"] = False
    with pytest.raises(ValueError):
        check_approval(quote, approval, request, "NQ")


def test_degraded_conditions_do_not_produce_usable_quote(tmp_path):
    transport = MetadataTransport()
    transport.condition = "degraded"
    report = DatabentoAccess(key="fixture", transport=transport).preflight(tmp_path, contract="NQH5", instrument="NQ", start="2025-01-02T00:00Z", end="2025-01-03T00:00Z")
    assert report["status"] == "DATA_BLOCKED"
    assert "timeseries" not in " ".join(transport.calls)


def test_unapproved_metered_request_never_reaches_transport(tmp_path):
    transport = MetadataTransport()
    with pytest.raises(ValueError, match="approval"):
        DatabentoBars(key="fixture", transport=transport).download(tmp_path, contract="NQH5", instrument="NQ",
                       start="2025-01-02T00:00Z", end="2025-01-03T00:00Z", license_scope="fixture")
    for invalid in (1024.5, -1, float("inf")):
        with pytest.raises(ValueError, match="memory budget"):
            DatabentoBars(key="fixture", transport=transport).download(tmp_path, contract="NQH5", instrument="NQ",
                       start="2025-01-02T00:00Z", end="2025-01-03T00:00Z", license_scope="fixture", max_response_bytes=invalid)
    assert transport.calls == []


def test_failed_consumption_is_not_automatically_retried_and_raw_is_preserved(tmp_path):
    quote, approval = approved_fixture(tmp_path)
    class BadBars:
        calls = 0
        def get(self, *args, **kwargs):
            self.calls += 1
            return SimpleNamespace(status_code=200, content=b"invalid-bar-payload")
    transport = BadBars()
    client = DatabentoBars(key="fixture", transport=transport)
    args = dict(contract="NQH5", instrument="NQ", start="2025-01-02T00:00Z", end="2025-01-03T00:00Z", license_scope="fixture", quote=quote, approval=approval)
    with pytest.raises(ValueError): client.download(tmp_path / "bars", **args)
    with pytest.raises(ValueError, match="reserved"): client.download(tmp_path / "bars", **args)
    assert transport.calls == 1
    assert [p.read_bytes() for p in (tmp_path / "bars/objects").iterdir()] == [b"invalid-bar-payload"]
    assert not list((tmp_path / "bars").glob("*.json"))


@pytest.mark.parametrize("row", ["2025-01-02T14:30:01Z,100,101,99,100,1,NQH5", "2025-01-02T14:30:00Z,100,101,99,100,0.5,NQH5"])
def test_non_aligned_minutes_and_fractional_contract_volume_are_rejected(row):
    raw = ("ts_event,open,high,low,close,volume,symbol\n" + row + "\n").encode()
    with pytest.raises(ValueError):
        normalize_csv(raw, "NQH5", pd.Timestamp("2025-01-02T00:00Z"), pd.Timestamp("2025-01-03T00:00Z"))


def test_missing_symbol_cannot_be_relabelled_as_requested_contract():
    raw = b"ts_event,open,high,low,close,volume,instrument_id\n2025-01-02T14:30:00Z,100,101,99,100,1,123\n"
    args = (raw, "NQH5", pd.Timestamp("2025-01-02T00:00Z"), pd.Timestamp("2025-01-03T00:00Z"))
    with pytest.raises(ValueError, match="identity"): normalize_csv(*args)
    with pytest.raises(ValueError, match="instrument ID"): normalize_csv(*args, expected_instrument_id=999)
    assert len(normalize_csv(*args, expected_instrument_id=123)) == 1


def test_response_byte_budget_preserves_bounded_prefix_and_closes_stream(tmp_path):
    quote, approval = approved_fixture(tmp_path)
    class Stream:
        status_code = 200
        closed = False
        def iter_content(self, size): yield b"x" * 2048
        def close(self): self.closed = True
    response = Stream()
    class Transport:
        def get(self, *args, **kwargs): return response
    with pytest.raises(ValueError, match="byte budget"):
        DatabentoBars(key="fixture", transport=Transport()).download(tmp_path / "bars", contract="NQH5", instrument="NQ",
                  start="2025-01-02T00:00Z", end="2025-01-03T00:00Z", license_scope="fixture",
                  quote=quote, approval=approval, max_response_bytes=1024)
    assert response.closed
    assert next((tmp_path / "bars/partial_objects").iterdir()).stat().st_size == 1024


def test_zero_cost_still_requires_explicit_credit_consumption_permission(tmp_path):
    from nocturne.adapters.snapshots import canonical, digest
    quote, approval = approved_fixture(tmp_path)
    quote["cost_usd"] = "0"
    quote.pop("quote_id")
    quote["quote_id"] = digest(canonical(quote))
    approval.update(quote_id=quote["quote_id"], authorized=False)
    with pytest.raises(ValueError, match="operator approval"):
        check_approval(quote, approval, quote["request"], "NQ")


@pytest.mark.parametrize("cost", [float("nan"), -1, "not-numeric"])
def test_invalid_provider_cost_is_blocked_not_treated_as_free(tmp_path, cost):
    transport = MetadataTransport()
    transport.cost = cost
    result = DatabentoAccess(key="fixture", transport=transport).preflight(tmp_path, contract="NQH5", instrument="NQ",
                              start="2025-01-02T00:00Z", end="2025-01-03T00:00Z")
    assert result["status"] == "DATA_BLOCKED"


def test_http_entitlement_failure_does_not_store_error_body_or_secret(tmp_path):
    class Denied:
        def get(self, *args, **kwargs):
            return SimpleNamespace(status_code=403, content=b"sensitive-error-fixture")
    result = DatabentoAccess(key="synthetic-secret", transport=Denied()).preflight(tmp_path, contract="NQH5", instrument="NQ",
                                  start="2025-01-02T00:00Z", end="2025-01-03T00:00Z")
    assert result["reason"] == "METADATA_HTTP_403"
    assert "synthetic-secret" not in json.dumps(result)
    assert "sensitive-error-fixture" not in json.dumps(result)
    assert not (tmp_path / "objects").exists()


def test_partial_contract_resolution_blocks_quote(tmp_path):
    class Partial(MetadataTransport):
        def post(self, url, **kwargs):
            value = super().post(url, **kwargs).json()
            value["partial"] = [kwargs["data"]["symbols"]]
            return SimpleNamespace(status_code=200, content=json.dumps(value).encode(), json=lambda: value)
    result = DatabentoAccess(key="fixture", transport=Partial()).preflight(tmp_path, contract="NQH5", instrument="NQ",
                                  start="2025-01-02T00:00Z", end="2025-01-03T00:00Z")
    assert result["status"] == "DATA_BLOCKED"
    assert result["reason"] == "RAW_CONTRACT_NOT_FULLY_RESOLVED"
