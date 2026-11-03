import pandas as pd
import pytest

from nocturne.research.labels import triple_barrier_labels


def bars(rows):
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close"])


def atr(values):
    return pd.Series(values, dtype=float)


def test_target_first_label():
    frame = bars(
        [
            ["2026-01-01", 100, 101, 99, 100],
            ["2026-01-02", 100, 101, 99.5, 100],
            ["2026-01-05", 100, 103, 99.5, 102],
        ]
    )
    labels = triple_barrier_labels(frame, atr([1, 1, 1]), target_atr=2, stop_atr=1, horizon=3)
    first = labels.iloc[0]
    assert first["entry_price"] == 100
    assert first["target"] == 102
    assert first["stop"] == 99
    assert first["outcome"] == "TP_FIRST"


def test_stop_first_label():
    frame = bars(
        [
            ["2026-01-01", 100, 101, 99, 100],
            ["2026-01-02", 100, 101, 99.5, 100],
            ["2026-01-05", 100, 101, 98, 99],
        ]
    )
    labels = triple_barrier_labels(frame, atr([1, 1, 1]), target_atr=2, stop_atr=1, horizon=3)
    assert labels.iloc[0]["outcome"] == "SL_FIRST"


def test_same_bar_hit_is_ambiguous():
    frame = bars(
        [
            ["2026-01-01", 100, 101, 99, 100],
            ["2026-01-02", 100, 101, 99.5, 100],
            ["2026-01-05", 100, 103, 98, 100],
        ]
    )
    labels = triple_barrier_labels(frame, atr([1, 1, 1]), target_atr=2, stop_atr=1, horizon=3)
    assert labels.iloc[0]["outcome"] == "AMBIGUOUS"


def test_timeout_label():
    frame = bars(
        [
            ["2026-01-01", 100, 100.5, 99.5, 100],
            ["2026-01-02", 100, 100.5, 99.5, 100],
            ["2026-01-05", 100, 100.5, 99.5, 100],
        ]
    )
    labels = triple_barrier_labels(frame, atr([1, 1, 1]), target_atr=2, stop_atr=1, horizon=3)
    assert labels.iloc[0]["outcome"] == "TIMEOUT"
