from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from nocturne.instruments import get_instrument
from nocturne.research.target_dataset import (
    TargetDatasetConfig,
    build_strategy_target_dataset,
)
from nocturne.strategies.base import Signal, TargetSpec

UTC = timezone.utc
NQ = get_instrument("NQ")
START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def bar(ts, o, h, l, c):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": 100,
    }


def signal(targets=(106.0, 109.0), horizon=6):
    return Signal(
        strategy_id="test",
        strategy_version="0.1",
        instrument_id="NQ",
        asof=START + timedelta(minutes=5),
        side="LONG",
        entry_low=103.0,
        entry_high=103.0,
        stop=100.0,
        targets=tuple(TargetSpec(f"TP{i + 1}", p, 1.0 + i) for i, p in enumerate(targets)),
        horizon_bars=horizon,
        reason_codes=("TEST",),
    )


def test_target_first_dataset():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 106.5, 102, 106),
            bar(START + timedelta(minutes=10), 106, 109.5, 105, 109),
        ]
    )
    frame = build_strategy_target_dataset([signal()], bars, NQ, TargetDatasetConfig(horizon_bars=2))
    assert len(frame) == 2
    first = frame.iloc[0]
    assert first["entry_price"] == 103
    assert bool(first["target_first"]) is True
    assert first["outcome"] == "TP_FIRST"
    assert first["mfe_r"] >= 1
    assert bool(frame.iloc[1]["target_first"]) is True


def test_stop_first_dataset():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 103.5, 99, 99.5),
        ]
    )
    frame = build_strategy_target_dataset([signal(targets=(106.0,))], bars, NQ)
    assert frame.iloc[0]["outcome"] == "SL_FIRST"
    assert bool(frame.iloc[0]["target_first"]) is False


def test_entry_is_next_bar_open_not_signal_bar():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 104, 104.5, 103.5, 104),
        ]
    )
    frame = build_strategy_target_dataset([signal(targets=(110.0,))], bars, NQ)
    assert frame.iloc[0]["entry_price"] == 104
    assert frame.iloc[0]["entry_time"] == bars.iloc[1]["timestamp"]


def test_timeout_dataset():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 103.5, 102.5, 103),
            bar(START + timedelta(minutes=10), 103, 103.5, 102.5, 103),
        ]
    )
    frame = build_strategy_target_dataset([signal(targets=(110.0,), horizon=2)], bars, NQ,
                                          TargetDatasetConfig(horizon_bars=2))
    assert frame.iloc[0]["outcome"] == "TIMEOUT"
    assert bool(frame.iloc[0]["target_first"]) is False


def test_truncated_horizon_is_censored_and_not_stop_loss():
    bars = pd.DataFrame([bar(START + timedelta(minutes=5), 103, 104, 102, 103)])
    result = build_strategy_target_dataset([signal(targets=(110.0,))], bars, NQ)
    assert result.iloc[0].outcome == "CENSORED"
    assert pd.isna(result.iloc[0].target_first)


def test_bar_after_exact_horizon_does_not_count():
    bars = pd.DataFrame([bar(START + timedelta(minutes=5), 103, 104, 102, 103),
                         bar(START + timedelta(minutes=10), 103, 111, 102, 110)])
    result = build_strategy_target_dataset([signal(targets=(110.0,))], bars, NQ,
                                           TargetDatasetConfig(horizon_bars=1))
    assert result.iloc[0].outcome == "TIMEOUT"
