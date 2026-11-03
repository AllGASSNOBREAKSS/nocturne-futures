"""Synthetic HTTP fixtures; these tests do not establish provider entitlement."""
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from nocturne.adapters.databento import DatabentoBars, aggregate_five_minutes
from nocturne.adapters.alfred import fetch_vintage, visible_vintages


class Transport:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_download_resume_and_raw_contract_provenance(tmp_path):
    payload = b"ts_event,open,high,low,close,volume,symbol\n2025-01-02T14:30:00Z,100,102,99,101,10,NQH5\n"
    transport = Transport(SimpleNamespace(status_code=200, content=payload))
    provider = DatabentoBars(key="synthetic-fixture-not-a-key", transport=transport)
    kwargs = dict(contract="NQH5", instrument="NQ", start="2025-01-02T00:00Z",
                  end="2025-01-03T00:00Z", license_scope="synthetic_test_fixture")
    first = provider.download(tmp_path, **kwargs)
    assert first == provider.download(tmp_path, **kwargs)
    assert len(transport.calls) == 1
    assert first[0]["ingestion"]["price_basis"] == "raw_contract"
    assert "synthetic-fixture-not-a-key" not in json.dumps(first)
    (tmp_path / first[0]["raw_file"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        provider.download(tmp_path, **kwargs)


def test_aggregation_rejects_missing_minutes_and_contract_mixing():
    stamps = pd.date_range("2025-01-01", periods=10, freq="1min", tz="UTC")
    frame = pd.DataFrame(dict(timestamp=stamps, available_at=stamps + pd.Timedelta("1min"),
                              open=100, high=102, low=99, close=101, volume=10, contract_id="NQH5"))
    assert aggregate_five_minutes(frame).volume.tolist() == [50, 50]
    assert len(aggregate_five_minutes(frame.drop(index=2))) == 1
    frame.loc[2, "contract_id"] = "NQM5"
    assert len(aggregate_five_minutes(frame)) == 1


def test_vintage_is_not_available_on_observation_date_or_same_release_day():
    response = {"count": 1, "observations": [{"date": "2025-01-01", "value": "3.2",
                 "realtime_start": "2025-02-10", "realtime_end": "2025-02-10"}]}
    transport = Transport(SimpleNamespace(status_code=200, json=lambda: response))
    records = fetch_vintage("TEST", "2025-02-10", key="fixture", transport=transport)
    assert visible_vintages(records, "2025-02-10T23:59Z").empty
    assert visible_vintages(records, "2025-02-11T00:00Z").value.tolist() == [3.2]
    assert records[0]["consensus"] is None
