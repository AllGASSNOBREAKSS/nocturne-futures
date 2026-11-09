"""Phase 3V: free futures parsing, roll handling, path resolution and ranking."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nocturne.adapters.databento_access import DatabentoAccess
from nocturne.collector.sources import parse_yahoo_chart
from nocturne.research import futures_free as ff

ROOT = Path(__file__).resolve().parents[1]


def chart(symbol, stamps, rows):
    quote = {k: [r[i] for r in rows] for i, k in enumerate(("open", "high", "low", "close", "volume"))}
    return json.dumps({"chart": {"result": [{"meta": {"symbol": symbol, "exchangeTimezoneName": "America/New_York"},
                                             "timestamp": stamps, "indicators": {"quote": [quote]}}]}}).encode()


def test_yahoo_parser_drops_incomplete_partial_and_flags_inconsistent_bars():
    base = 1_793_000_100  # aligned to 300 s
    payload = chart("NQ=F", [base, base + 300, base + 600, base + 777],
                    [(10, 11, 9, 10.5, 5), (None, 11, 9, 10, 5), (10, 9, 11, 10, 5), (10, 12, 9, 11, 5)])
    frame, meta = parse_yahoo_chart(payload, "NQ=F", 300, now=pd.Timestamp(base + 10_000, unit="s", tz="UTC"))
    assert len(frame) == 2  # incomplete-OHLC bar dropped, unaligned live bar dropped
    assert meta["dropped_incomplete_bars"] == 1
    assert frame.ohlc_consistent.tolist() == [True, False]
    with pytest.raises(ValueError, match="identity"):
        parse_yahoo_chart(payload, "ES=F", 300)


def test_roll_dates_require_matching_checksum(tmp_path):
    body = json.dumps({"result": {"NQ.v.0": [{"d0": "2026-03-01"}, {"d0": "2026-06-17"}, {"d0": "2026-09-16"}]}}).encode()
    digest = hashlib.sha256(body).hexdigest()
    (tmp_path / "objects").mkdir()
    (tmp_path / "objects" / digest).write_bytes(body)
    report = tmp_path / "pre.json"
    report.write_text(json.dumps({"metadata_receipts": [{"method": "symbology.resolve", "body_sha256": digest}]}))
    assert [str(d) for d in ff.roll_dates(report, tmp_path, "NQ.v.0")] == ["2026-06-17", "2026-09-16"]
    (tmp_path / "objects" / digest).write_bytes(body + b" ")
    with pytest.raises(ValueError, match="checksum"):
        ff.roll_dates(report, tmp_path, "NQ.v.0")


def bars(rows, start="2026-10-20 15:00", freq="1h"):
    index = pd.date_range(start, periods=len(rows), freq=freq, tz="UTC")
    return pd.DataFrame({"timestamp": index, "open": [r[0] for r in rows], "high": [r[1] for r in rows],
                         "low": [r[2] for r in rows], "close": [r[3] for r in rows]})


def test_target_stop_resolution_uses_fine_bars_then_conservative_stop():
    path = bars([(100, 230, 0, 120)])  # hourly bar touches +100 target and -100 stop
    empty = {"1m": bars([], freq="1min"), "5m": bars([], freq="5min")}
    assert ff.resolve(path, empty, 100, 100, 100, "LONG")[:2] == ("STOP_FIRST", "AMBIGUOUS_HOURLY_STOP_FIRST")
    fine = bars([(100, 205, 95, 200)] + [(200, 200, -5, 0)] + [(0, 1, -1, 0)] * 58, freq="1min")
    outcome, how, _ = ff.resolve(path, {"1m": fine, "5m": empty["5m"]}, 100, 100, 100, "LONG")
    assert (outcome, how) == ("TARGET_FIRST", "RESOLVED_1m")
    assert ff.resolve(bars([(100, 150, 50, 120)] * 3), empty, 100, 100, 100, "SHORT")[0] == "TIMEOUT"


def test_wilson_interval_bounds():
    assert ff.wilson(0, 0)["p"] is None
    cell = ff.wilson(5, 10)
    assert cell["p"] == .5 and 0 < cell["ci95"][0] < .5 < cell["ci95"][1] < 1


def test_family_increment_verdicts():
    years = [2010] * 300 + [2025] * 300
    y = np.tile([0, 1], 300)
    ref = pd.DataFrame({"date": pd.date_range("2010-01-01", periods=600).date, "year": years, "y": y, "p_model": .5})
    better = ref.assign(p_model=np.where(y == 1, .7, .3))
    assert ff.increment(better, ref)["verdict"] == "FAMILY_HELPS"
    worse = ref.assign(p_model=np.where(y == 1, .3, .7))
    assert ff.increment(worse, ref)["verdict"] == "FAMILY_HURTS"


def test_ranking_requires_positive_lower_bounds_in_both_eras():
    spec = importlib.util.spec_from_file_location("rank", ROOT / "scripts/phase3v_rank.py")
    rank = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rank)
    assert rank.reason([1, 2], [1, 2], 100, 100) is None
    assert rank.reason([1, 2], [1, 2], 99, 100) == "INSUFFICIENT_SAMPLE"
    assert rank.reason([-1, 2], [1, 2], 200, 200).startswith("DEVELOPMENT")
    assert rank.reason([1, 2], [0, 2], 200, 200).startswith("HOLDOUT")


class Recorder:
    def __init__(self, payloads):
        self.payloads = payloads

    def get(self, url, params=None, auth=None, timeout=None):
        method = url.rsplit("/", 1)[-1]
        body = json.dumps(self.payloads[method]).encode()
        return type("R", (), {"status_code": 200, "content": body, "json": lambda self, b=body: json.loads(b)})()


def test_preflight_accepts_current_schema_range_key(tmp_path):
    payloads = {"metadata.list_datasets": ["GLBX.MDP3"], "metadata.list_schemas": ["ohlcv-1m"],
                "metadata.get_dataset_range": {"start": "2010-06-06T00:00:00Z", "end": "2026-11-08T00:00:00Z",
                                               "schema": {"ohlcv-1m": {"start": "2010-06-06T00:00:00Z", "end": "2026-11-08T00:00:00Z"}}},
                "metadata.get_dataset_condition": []}
    report = DatabentoAccess(key="test-key", transport=Recorder(payloads)).preflight(
        tmp_path, contract="NQZ6", instrument="NQ", start="2026-11-02T00:00:00Z", end="2026-11-02T12:00:00Z")
    # Range check now passes; the empty condition list blocks next, before any cost call.
    assert report["reason"] == "PILOT_DATASET_CONDITION_UNAVAILABLE_OR_DEGRADED"
    assert report["time_series_requested"] is False and "test-key" not in json.dumps(report)
