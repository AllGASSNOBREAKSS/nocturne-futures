import numpy as np
import pandas as pd
import pytest

from nocturne.research.target_survival import (
    aalen_johansen, enrich_targets, event_rates, outcome_matrix,
)


def test_aalen_johansen_competing_risks_and_censoring():
    result = aalen_johansen([1, 1, 2, 3, 3], [1, 2, 1, 0, 0], horizon=3)
    # t=1: 5 at risk, one target and one stop -> 0.2 each; survival 0.6.
    # t=2: 3 at risk, one target -> +0.6/3 = 0.2; survival 0.4.
    # t=3: both remaining rows censored -> survival 0.
    assert result["incidence"]["TARGET_FIRST"] == pytest.approx(0.4)
    assert result["incidence"]["STOP_FIRST"] == pytest.approx(0.2)
    assert result["neither"] == pytest.approx(0.4)
    assert result["at_risk_start"] == 5
    assert sum(result["incidence"].values()) + result["neither"] == pytest.approx(1.0)


def test_aalen_johansen_rejects_bad_input():
    with pytest.raises(ValueError):
        aalen_johansen([1, 2], [1], horizon=2)
    with pytest.raises(ValueError):
        aalen_johansen([0, 1], [1, 2])
    with pytest.raises(ValueError):
        aalen_johansen([1, 2], [1, 5])


def test_enrichment_uses_only_bars_available_at_signal():
    stamps = pd.date_range("2025-01-02T14:30Z", periods=40, freq="5min")
    bars = pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                         "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10})
    frame = pd.DataFrame([{
        "signal_id": "s", "strategy_id": "vwap", "feature_available_at": stamps[20] + pd.Timedelta("5min"),
        "label_end": stamps[30], "entry_price": 100.0, "stop_price": 98.0, "target_price": 104.0,
        "side": "LONG", "outcome": "TP_FIRST", "bars_to_target": 3, "bars_to_stop": None,
        "horizon_bars": 24, "horizon_complete": True,
    }])
    enriched = enrich_targets(frame, bars)
    # ATR of a constant 2-point true range is exactly 2 points.
    assert enriched.atr_points.iloc[0] == pytest.approx(2.0)
    assert enriched.target_atr.iloc[0] == pytest.approx(2.0)
    assert enriched.stop_atr.iloc[0] == pytest.approx(1.0)
    assert enriched.event.iloc[0] == 1
    # Mutating the future cannot change features.
    changed = bars.copy()
    changed.loc[21:, ["open", "high", "low", "close"]] += 500
    second = enrich_targets(frame, changed)
    assert second.atr_points.iloc[0] == pytest.approx(2.0)


def test_event_rates_separate_ambiguous_and_censored():
    frame = pd.DataFrame({"outcome": ["TP_FIRST", "SL_FIRST", "TIMEOUT", "CENSORED", "AMBIGUOUS"],
                          "event": [1, 2, 0, 0, 0], "ambiguous": [False, False, False, False, True],
                          "censored": [False, False, False, True, False], "horizon_complete": [True] * 5})
    rates = event_rates(frame)
    assert rates["resolved_rows"] == 3
    assert rates["target_share"] == pytest.approx(1 / 3)
    assert rates["ambiguous"] == 1 and rates["censored"] == 1
    matrix = outcome_matrix(frame)
    assert matrix.sum() == len(frame)
    assert matrix[0].tolist() == [1, 0, 0]
