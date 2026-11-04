from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nocturne.adapters.yahoo_history import _frame
from nocturne.research.analogues import analogue_probabilities, build_windows
from nocturne.research.level_reactions import LevelEventConfig, level_events, summarize_events, wilson
from nocturne.research.seasonality import _bh, prepare, summarize

UTC = timezone.utc


def payload(stamps, closes, highs=None, lows=None):
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    return {"chart": {"result": [{
        "meta": {"dataGranularity": "1d"},
        "timestamp": [int(pd.Timestamp(s, tz="UTC").timestamp()) for s in stamps],
        "indicators": {"quote": [{"open": closes, "high": highs, "low": lows,
                                  "close": closes, "volume": [10] * len(closes)}]},
    }]}}


def test_daily_frame_handles_pre_1970_dates_and_drops_invalid_bars():
    frame = _frame(payload(["1960-01-04", "1960-01-05"], [10.0, 11.0],
                           highs=[10.5, 10.0], lows=[9.5, 10.5]), "TEST")
    # The second bar has high below open/close and is dropped, not repaired.
    assert len(frame) == 1
    assert frame.date.iloc[0] == "1960-01-04"
    assert frame.available_at.iloc[0] == pd.Timestamp("1960-01-05", tz="UTC")


def test_daily_frame_rejects_duplicate_dates():
    with pytest.raises(ValueError, match="duplicate"):
        _frame(payload(["2020-01-02", "2020-01-02"], [10.0, 11.0]), "TEST")


def test_bh_adjustment_is_monotone_and_bounded():
    adjusted = _bh([0.01, 0.04, 0.03, 0.2])
    assert all(0 <= value <= 1 for value in adjusted)
    assert adjusted[0] <= adjusted[2] <= adjusted[3]


def test_seasonality_requires_minimum_sample_and_reports_intervals():
    stamps = pd.date_range("2010-01-01", periods=800, freq="B")
    closes = 100 + np.arange(800) * 0.01
    frame = pd.DataFrame({"date": stamps.strftime("%Y-%m-%d"), "open": closes, "high": closes + 1,
                          "low": closes - 1, "close": closes, "volume": 10})
    result = summarize(frame)
    assert result["rows"] > 700
    assert result["effects"]["weekday"]["groups"]
    for group in result["effects"]["weekday"]["groups"]:
        assert group["year_block_low"] is None or group["year_block_low"] <= group["mean_return"]
        assert "p_value_bh" in group


def test_wilson_interval_bounds():
    low, high = wilson(0, 10)
    assert 0 <= low <= high <= 1
    assert wilson(0, 0) == (None, None)


class Level:
    def __init__(self, price, level_type="POC"):
        self.price = price
        self.level_id = f"{level_type}-{price}"
        self.level_type = level_type


def bars(path):
    stamps = pd.date_range("2026-01-02T14:30Z", periods=len(path), freq="5min")
    return pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                         "open": [p[0] for p in path], "high": [p[1] for p in path],
                         "low": [p[2] for p in path], "close": [p[3] for p in path], "volume": 10})


def test_level_events_distinguish_acceptance_and_breakthrough():
    frame = bars([(100, 101, 99, 100), (100, 102, 99, 101), (101, 103, 100, 102),
                  (102, 104, 101, 103), (103, 105, 102, 104), (104, 106, 103, 105)])
    asof = frame.available_at.iloc[0]
    events = level_events(frame, [Level(101.0)], asof, atr=1.0)
    row = events.iloc[0]
    assert row.touched and row.bars_to_touch == 0
    assert row.acceptance and row.break_through
    assert row.target_before_stop is None or isinstance(row.target_before_stop, (bool, np.bool_))


def test_level_events_ignore_future_bars_for_features():
    frame = bars([(100, 101, 99, 100), (100, 102, 99, 101), (101, 103, 100, 102)])
    asof = frame.available_at.iloc[0]
    first = level_events(frame, [Level(103.0)], asof, atr=1.0)
    changed = frame.copy()
    changed.loc[2, ["open", "high", "low", "close"]] = [200, 205, 195, 200]
    second = level_events(changed, [Level(103.0)], asof, atr=1.0)
    assert first.distance_atr.iloc[0] == second.distance_atr.iloc[0]
    assert summarize_events(first)["rows"] == 1


def test_committed_daily_manifests_match_stored_bytes():
    import hashlib
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "data/history/yahoo_daily"
    manifests = sorted((root / "manifests").glob("*.json"))
    assert manifests
    for manifest in manifests:
        meta = json.loads(manifest.read_text())
        raw = list((root / "raw").glob("*" + meta["raw_sha256"] + "*"))
        assert len(raw) == 1
        assert hashlib.sha256(raw[0].read_bytes()).hexdigest() == meta["raw_sha256"]
        name = meta["symbol"].replace("^", "IDX_").replace("=", "_")
        normalized = root / "normalized" / (name + ".csv")
        assert hashlib.sha256(normalized.read_bytes()).hexdigest() == meta["normalized_sha256"]
