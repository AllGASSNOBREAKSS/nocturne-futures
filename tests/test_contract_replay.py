import json

import pandas as pd
import pytest

from nocturne.adapters.databento import normalize_csv, aggregate_five_minutes
from nocturne.adapters.snapshots import digest
from nocturne.instruments import get_instrument
from nocturne.research.contract_replay import load_contract_receipts, asof_contract_context, target_distance_study
from nocturne.research.contract_targets import ContractSetup

NQ = get_instrument("NQ")


def write_receipt(root):
    root.mkdir(parents=True, exist_ok=True)
    stamps = pd.date_range("2026-11-02T14:30:00Z", periods=120, freq="1min")
    frame = pd.DataFrame({"ts_event": stamps, "symbol": "NQZ6", "open": 20000., "high": 20001., "low": 19999., "close": 20000., "volume": 10})
    raw = frame.to_csv(index=False).encode()
    (root / "fixture.csv").write_bytes(raw)
    start, end = stamps[0], stamps[-1] + pd.Timedelta("1min")
    normalized = normalize_csv(raw, "NQZ6", start, end).to_csv(index=False, lineterminator="\n").encode()
    (root / "fixture.normalized.csv").write_bytes(normalized)
    receipt = {"request": {"dataset": "GLBX.MDP3", "stype_in": "raw_symbol", "schema": "ohlcv-1m", "symbols": "NQZ6",
                           "start": start.isoformat(), "end": end.isoformat()},
               "instrument": "NQ", "license_scope": "synthetic-fixture-only", "raw_file": "fixture.csv", "raw_sha256": digest(raw),
               "export_file": "fixture.normalized.csv", "export_sha256": digest(normalized), "received_at": "2026-11-03T00:00:00Z",
               "availability": "bar-end lower bound; fixture only"}
    (root / "fixture.json").write_text(json.dumps(receipt))
    return load_contract_receipts(root, NQ, "NQZ6")


def test_receipt_replay_is_causal_and_does_not_invent_orderflow(tmp_path):
    history = write_receipt(tmp_path)
    asof = pd.Timestamp("2026-11-02T15:00:00Z")
    context = asof_contract_context(history, NQ, "NQZ6", asof.date(), "NEW_YORK", asof)
    assert context["bars_available"] == 30
    assert context["missing_minute_bars"] == 0
    assert context["poc"] is None and context["cvd"] is None and context["true_vwap"] is None
    changed = {**history, "bars": history["bars"].copy()}
    changed["bars"].loc[changed["bars"].available_at > asof, ["open", "high", "low", "close"]] += 500
    assert asof_contract_context(changed, NQ, "NQZ6", asof.date(), "NEW_YORK", asof) == context


def test_corrupt_receipt_and_overlapping_chunks_are_rejected(tmp_path):
    write_receipt(tmp_path)
    (tmp_path / "fixture.csv").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        load_contract_receipts(tmp_path, NQ, "NQZ6")
    write_receipt(tmp_path)
    (tmp_path / "duplicate.json").write_bytes((tmp_path / "fixture.json").read_bytes())
    with pytest.raises(ValueError, match="overlapping"):
        load_contract_receipts(tmp_path, NQ, "NQZ6")


def test_nq_target_grid_uses_existing_labels_and_keeps_probabilities_null(tmp_path):
    history = write_receipt(tmp_path)
    setup = ContractSetup("fixture", "NQZ6", "2026-11-02T15:00:00Z", "LONG", 20000., 19990., (20010.,),
                          features={"unverified_future_feature": 99})
    rows = target_distance_study(history, NQ, [setup], horizons=(12, 24))
    assert len(rows) == 10
    assert set(rows.requested_distance_points) == {50., 100., 200., 350., 500.}
    assert rows.target_first_probability.isna().all()
    assert not any(column.startswith("feature_") for column in rows if column != "feature_available_at")
    assert set(rows.promotion_status) == {"NO_PROMOTION"}


def test_absent_contract_data_is_blocked_not_a_synthetic_dataset(tmp_path):
    history = load_contract_receipts(tmp_path, NQ, "NQZ6")
    assert history["status"] == "DATA_BLOCKED"
    assert target_distance_study(history, NQ, []).empty


@pytest.mark.parametrize("case", ["negative_volume", "bad_high", "duplicate"])
def test_raw_contract_normalization_rejects_bad_observations(case):
    row = {"ts_event": "2026-11-02T14:30:00Z", "symbol": "NQZ6", "open": 100., "high": 101., "low": 99., "close": 100., "volume": 10}
    if case == "negative_volume":
        row["volume"] = -1
    if case == "bad_high":
        row["high"] = 90
    raw = pd.DataFrame([row, row] if case == "duplicate" else [row]).to_csv(index=False).encode()
    with pytest.raises(ValueError, match="invalid"):
        normalize_csv(raw, "NQZ6", pd.Timestamp("2026-11-02T14:30:00Z"), pd.Timestamp("2026-11-02T14:31:00Z"))


def test_nanosecond_timestamps_are_not_dropped_as_incomplete_minutes(tmp_path):
    history = write_receipt(tmp_path)
    frame = history["bars"].iloc[:5].copy()
    frame["timestamp"] = frame.timestamp.astype("datetime64[ns, UTC]")
    assert len(aggregate_five_minutes(frame)) == 1


def test_target_grid_atr_is_derived_only_from_available_contract_bars(tmp_path):
    history = write_receipt(tmp_path)
    setup = ContractSetup("fixture", "NQZ6", "2026-11-02T16:00:00Z", "LONG", 20000., 19990., (20010.,),
                          features={"atr": 9999.})
    rows = target_distance_study(history, NQ, [setup], horizons=(12,))
    assert set(rows.feature_atr) == {2.}
    assert rows.target_distance_atr.notna().all()
    assert (pd.to_datetime(rows.derived_atr_available_at, utc=True) <= pd.Timestamp(setup.asof)).all()
