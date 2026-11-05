import copy
import json

import pandas as pd
import pytest

from nocturne.adapters.snapshots import canonical
from nocturne.adapters.yahoo_history import _frame
from nocturne.shadow import evaluate_matured, evaluation_summary
from nocturne.shadow.outcome_audit import audit_outcomes
from test_market_snapshots import evidence, payload


def matured_fixture(tmp_path):
    archive, store, ids, forecast = evidence(tmp_path)
    raw = payload()
    result = raw["chart"]["result"][0]
    result["timestamp"].append(int(pd.Timestamp("2025-03-25T13:30:00Z").timestamp()))
    for key, value in {"open": 500., "high": 510., "low": 490., "close": 505., "volume": 1000}.items():
        result["indicators"]["quote"][0][key].append(value)
    source = {"symbol": "^NDX", "provider": "yahoo_public_unofficial", "frequency": "1d", "session": "US_cash_daily",
              "price_basis": "provider_quote_ohlc_not_adjclose", "timezone": "America/New_York", "received_at": "2025-03-26T01:00:00Z"}
    identifier = archive.capture(canonical(raw), _frame(raw, "^NDX").to_csv(index=False).encode(), source)
    frame = archive.frame(identifier)
    frame.attrs["snapshot_id"] = identifier
    written = evaluate_matured(store, frame, pd.Timestamp("2025-03-26T02:00:00Z").to_pydatetime())
    assert len(written) == 1
    return archive, store, forecast


def test_verified_outcome_recomputes_units_without_modifying_journals(tmp_path):
    archive, store, forecast = matured_fixture(tmp_path)
    before = store.forecast_path.read_bytes(), store.outcome_path.read_bytes()
    report = audit_outcomes(store, archive, {"p50": .01, "p80": .02, "p90": .03})
    assert report["verified"] == 1
    checked = report["records"][0]
    assert checked["realized_range_points"] == 20
    assert checked["realized_range_pct"] == pytest.approx(20 / forecast["reference_close"])
    assert (store.forecast_path.read_bytes(), store.outcome_path.read_bytes()) == before


@pytest.mark.parametrize("field,value", [("realized_range_points", 999.), ("source_available_at", "2025-03-25T00:00:00Z"),
                                        ("forecast_sha256", "bad"), ("outcome_bar_sha256", "bad")])
def test_corrupt_outcome_is_quarantined_not_repaired(tmp_path, field, value):
    archive, store, _ = matured_fixture(tmp_path)
    modified = {**store.outcomes()[0], field: value}
    store.outcome_path.write_text(json.dumps(modified) + "\n")
    report = audit_outcomes(store, archive)
    assert report["status"] == "AUDIT_BLOCKED" and report["verified"] == 0
    summary = evaluation_summary(store, verified_forecast_ids=set())
    assert summary["quarantined_outcomes"] == 1
    assert "coverage" not in summary
    assert json.loads(store.outcome_path.read_text())[field] == value


def test_duplicate_outcomes_cannot_double_count_verified_metrics(tmp_path):
    archive, store, _ = matured_fixture(tmp_path)
    content = store.outcome_path.read_bytes()
    store.outcome_path.write_bytes(content + content)
    report = audit_outcomes(store, archive)
    assert report["verified"] == 0
    assert report["status"] == "AUDIT_BLOCKED"


def test_first_legacy_comparator_is_explicitly_post_issuance(tmp_path):
    archive, store, _ = matured_fixture(tmp_path)
    forecast = store.forecasts()[0]
    forecast.pop("baseline_quantiles")
    forecast.pop("record_sha256")
    from nocturne.adapters.snapshots import digest
    store.forecast_path.write_text(json.dumps(forecast) + "\n")
    outcome = store.outcomes()[0]
    outcome["forecast_sha256"] = digest(canonical(forecast))
    store.outcome_path.write_text(json.dumps(outcome) + "\n")
    report = audit_outcomes(store, archive, {"p50": .01, "p80": .02, "p90": .03})
    assert report["records"][0]["baseline_comparison"]["registration"].startswith("POST_ISSUANCE")
