import pandas as pd
import pytest

from nocturne.adapters.history import ingest_export, bar_quality
from nocturne.adapters.fred import parse_series


def bars():
    stamps = pd.date_range("2026-01-02", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                         "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10,
                         "contract_id": "NQH6"})


def test_resumable_content_addressed_ingestion_and_conflicts(tmp_path):
    source = tmp_path / "export.csv"
    bars().to_csv(source, index=False)
    kwargs = dict(provider="authorized_fixture", instrument="NQ", interval="5min",
                  price_basis="raw_contract", license_scope="test")
    first = ingest_export(source, tmp_path / "history", **kwargs)
    assert first == ingest_export(source, tmp_path / "history", **kwargs)
    changed = bars()
    changed.loc[0, "close"] = 100.5
    changed.to_csv(source, index=False)
    with pytest.raises(ValueError, match="revisions"):
        ingest_export(source, tmp_path / "history", **kwargs)


def test_corrupt_ohlc_and_early_availability_detected():
    frame = bars()
    frame.loc[0, "high"] = 98
    frame.loc[1, "available_at"] = frame.loc[1, "timestamp"]
    assert bar_quality(frame)["invalid_rows"] == 2


def test_fred_missing_value_is_not_zero():
    frame = parse_series(b"observation_date,DGS10\n2026-01-01,.\n2026-01-02,4.1\n", "DGS10")
    assert pd.isna(frame.value.iloc[0])
    assert frame.value.iloc[1] == 4.1
