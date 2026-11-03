from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from nocturne.ml.target_model import evaluate_split
from nocturne.research.target_training import (
    expanding_folds,
    prepare_binary,
    split_by_signal,
)

UTC = timezone.utc


def target_frame(n_signals=60):
    rows = []
    for i in range(n_signals):
        asof = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i)
        y = i % 2
        for target in ("TP1", "TP2"):
            rows.append(
                {
                    "signal_id": f"s{i}",
                    "strategy_id": "vwap_value_aligned_pullback" if i % 2 else "opening_range_ib_breakout_retest",
                    "side": "LONG",
                    "signal_asof": asof,
                    "outcome": "TP_FIRST" if y else "SL_FIRST",
                    "y": y,
                    "atr_pct": 0.001 + i * 1e-6,
                    "risk_atr": 1.0,
                    "target_distance_atr": 1.5,
                    "r_multiple": 1.0 if target == "TP1" else 2.0,
                    "horizon_bars": 24,
                    "time_of_day_min": 60.0,
                    "rv20": 0.001,
                    "or15_size_atr": 1.0,
                    "ib60_size_atr": 2.0,
                    "dist_vwap_atr": 0.2,
                    "dist_poc_atr": 0.3,
                    "dist_vah_atr": 0.4,
                    "dist_val_atr": -0.4,
                    "dist_session_high_atr": -0.5,
                    "dist_session_low_atr": 0.5,
                    "dist_prior_high_atr": -0.6,
                    "dist_prior_low_atr": 0.6,
                    "dist_prior_close_atr": 0.1,
                    "dist_overnight_high_atr": -0.2,
                    "dist_overnight_low_atr": 0.2,
                    "mom5": 0.001,
                    "mom20": 0.002,
                    "trend_strength": 0.3,
                    "range_compression": 0.8,
                    "vol_percentile": 0.5,
                    "es_nq_relative_1h": 0.0,
                    "vix_level": 20.0,
                    "vix_change_5d": 0.01,
                }
            )
    return pd.DataFrame(rows)


def test_prepare_binary_adds_target_and_dummies():
    binary, features = prepare_binary(target_frame())
    assert set(binary["y"].unique()) == {0, 1}
    assert "strategy_vwap_value_aligned_pullback" in features
    assert "side_LONG" in features
    assert len(binary) == 120


def test_split_by_signal_keeps_signals_disjoint():
    binary, _ = prepare_binary(target_frame())
    train, validation, test = split_by_signal(binary)
    train_ids = set(train["signal_id"])
    validation_ids = set(validation["signal_id"])
    test_ids = set(test["signal_id"])
    assert not (train_ids & validation_ids)
    assert not (train_ids & test_ids)
    assert not (validation_ids & test_ids)
    assert train_ids | validation_ids | test_ids == set(binary["signal_id"])


def test_expanding_folds_are_chronological():
    binary, _ = prepare_binary(target_frame())
    folds = expanding_folds(binary, n_folds=3)
    assert len(folds) == 3
    previous_test_end = None
    for train, validation, test in folds:
        assert train["signal_asof"].max() <= test["signal_asof"].min()
        if previous_test_end is not None:
            assert test["signal_asof"].min() >= previous_test_end
        previous_test_end = test["signal_asof"].max()


def test_evaluate_split_probabilities_are_bounded():
    rng = np.random.default_rng(7)
    n = 120
    frame = pd.DataFrame(
        {
            "x1": rng.normal(size=n),
            "x2": rng.normal(size=n),
            "y": rng.integers(0, 2, size=n),
        }
    )
    train, validation, test = frame.iloc[:70], frame.iloc[70:95], frame.iloc[95:]
    results = evaluate_split(train, validation, test, ["x1", "x2"])
    for result in results.values():
        assert result.predictions["p"].between(0, 1).all()
        assert "brier" in result.metrics
