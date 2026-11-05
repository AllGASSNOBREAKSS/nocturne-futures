import json

import pandas as pd
import pytest

from nocturne.adapters.databento import normalize_csv
from nocturne.adapters.snapshots import digest
from nocturne.research.futures_pilot import run_pilot
from nocturne.instruments import get_instrument
from nocturne.market_clock import session_window


def fixture_receipt(root, count=390):
    root.mkdir()
    stamps = pd.date_range("2026-11-02T14:30:00Z", periods=count, freq="1min")
    price = 20000 + pd.Series(range(count)) * .25
    frame = pd.DataFrame({"ts_event": stamps, "symbol": "NQZ6", "open": price, "high": price + 1,
                          "low": price - 1, "close": price + .25, "volume": 10})
    raw = frame.to_csv(index=False).encode()
    start, end = stamps[0], stamps[-1] + pd.Timedelta("1min")
    normalized = normalize_csv(raw, "NQZ6", start, end).to_csv(index=False, lineterminator="\n").encode()
    (root / "fixture.csv").write_bytes(raw)
    (root / "fixture.normalized.csv").write_bytes(normalized)
    receipt = {"request": {"dataset": "GLBX.MDP3", "stype_in": "raw_symbol", "schema": "ohlcv-1m", "symbols": "NQZ6", "start": start.isoformat(), "end": end.isoformat()},
               "instrument": "NQ", "license_scope": "SYNTHETIC_TEST_ONLY", "raw_file": "fixture.csv", "raw_sha256": digest(raw),
               "export_file": "fixture.normalized.csv", "export_sha256": digest(normalized), "received_at": "2026-11-03T00:00Z"}
    (root / "fixture.json").write_text(json.dumps(receipt))


def test_absent_inventory_does_not_fabricate_empty_backtest_success(tmp_path):
    result = run_pilot(tmp_path, "NQ", "NQZ6", tmp_path / "out")
    assert result["status"] == "BLOCKED" and result["licensed_rows"] == 0
    assert result["survival_fit"] is None


def test_sparse_rth_is_blocked_not_forward_filled(tmp_path):
    root = tmp_path / "receipts"
    fixture_receipt(root, 120)
    result = run_pilot(root, "NQ", "NQZ6", tmp_path / "out")
    assert result["reason"] == "NO_COMPLETE_RTH_MINUTE_GRID"
    assert result["missing_rth_minutes"]["2026-11-02"] == 270


def test_full_fixture_reuses_strategy_engines_and_keeps_probabilities_null(tmp_path):
    root = tmp_path / "receipts"
    fixture_receipt(root)
    result = run_pilot(root, "NQ", "NQZ6", tmp_path / "out")
    assert result["status"] == "SUCCEEDED"
    assert result["scope"].startswith("PILOT_PLUMBING")
    assert set(result["strategies"]) == {"orb", "vwap"}
    assert result["target_first_probability"] is None
    assert result["decision"] == "NO_PROMOTION"
    assert result["strategies"]["orb"]["cost_sensitivity"]["1"]["trades"] > 0
    assert all(label["sha256"] for entry in result["strategies"].values() for label in entry["labels"])
    assert result["strategies"]["orb"]["cost_sensitivity"]["1"]["profit_factor"] is None
    json.dumps(result, default=str, allow_nan=False)


@pytest.mark.parametrize("day,open_utc", [("2026-03-09", "13:30"), ("2026-11-02", "14:30")])
def test_existing_session_clock_handles_dst_for_pilot_grid(day, open_utc):
    window = session_window(get_instrument("NQ"), "RTH", pd.Timestamp(day).date())
    assert window.start_utc.strftime("%H:%M") == open_utc
