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
    # t=3: both remaining rows censored -> survival remains 0.4.
    assert result["incidence"]["TARGET_FIRST"] == pytest.approx(0.4)
    assert result["incidence"]["STOP_FIRST"] == pytest.approx(0.2)
    assert result["neither"] == pytest.approx(0.4)
    assert result["at_risk_start"] == 5
    assert result["event_free_survival"] == pytest.approx(.4)
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


def test_censor_before_event_must_not_reduce_event_free_survival():
    result = aalen_johansen([1, 2], [0, 1], horizon=2)
    assert result["path"][0]["survival"] == 1.0
    assert result["incidence"]["TARGET_FIRST"] == 1.0
    assert result["neither"] == 0.0


@pytest.mark.parametrize("durations,events,horizon", [([1.5], [1], 2), ([1], [1.2], 2), ([1], [1], 0), ([1], [1], 1.5)])
def test_fractional_or_unsupported_event_time_inputs_are_rejected(durations, events, horizon):
    with pytest.raises(ValueError):
        aalen_johansen(durations, events, horizon)


def test_censored_duration_uses_observed_prefix_not_intended_horizon():
    stamps = pd.date_range("2025-01-02T14:30Z", periods=40, freq="5min")
    bars = pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                         "open": 100., "high": 101., "low": 99., "close": 100., "volume": 10})
    row = {"signal_id": "fixture", "strategy_id": "fixture", "feature_available_at": stamps[20],
           "label_end": stamps[23], "entry_price": 100., "stop_price": 98., "target_price": 104.,
           "side": "LONG", "outcome": "CENSORED", "bars_to_target": None, "bars_to_stop": None,
           "horizon_bars": 24, "horizon_complete": False, "observed_contiguous_bars": 3}
    assert enrich_targets(pd.DataFrame([row]), bars).duration_bars.iloc[0] == 3
    del row["observed_contiguous_bars"]
    unknown = enrich_targets(pd.DataFrame([row]), bars)
    assert pd.isna(unknown.duration_bars.iloc[0])
    assert unknown.duration_evidence.iloc[0].startswith("UNKNOWN")


def test_late_published_past_bar_cannot_leak_into_atr():
    stamps = pd.date_range("2025-01-02T14:30Z", periods=40, freq="5min")
    bars = pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                         "open": 100., "high": 101., "low": 99., "close": 100., "volume": 10})
    bars.loc[15, "available_at"] = stamps[-1] + pd.Timedelta("1D")
    row = {"signal_id": "fixture", "strategy_id": "fixture", "feature_available_at": stamps[22],
           "label_end": stamps[30], "entry_price": 100., "stop_price": 98., "target_price": 104.,
           "side": "LONG", "outcome": "TP_FIRST", "bars_to_target": 3, "bars_to_stop": None,
           "horizon_bars": 24, "horizon_complete": True}
    before = enrich_targets(pd.DataFrame([row]), bars)
    bars.loc[15, "high"] = 999.
    after = enrich_targets(pd.DataFrame([row]), bars)
    assert before.atr_points.iloc[0] == after.atr_points.iloc[0] == 2.
