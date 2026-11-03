from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from nocturne.backtest import BacktestConfig, run_signal
from nocturne.instruments import get_instrument
from nocturne.strategies.base import Signal, TargetSpec

UTC = timezone.utc
NQ = get_instrument("NQ")
ES = get_instrument("ES")
START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def bar(ts, o, h, l, c, v=100):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


def signal(
    entry=103.0,
    stop=100.0,
    targets=(106.0, 109.0),
    horizon=6,
    asof=START + timedelta(minutes=5),
):
    return Signal(
        strategy_id="test",
        strategy_version="0.1",
        instrument_id="NQ",
        asof=asof,
        side="LONG",
        entry_low=entry,
        entry_high=entry,
        stop=stop,
        targets=tuple(TargetSpec(f"TP{i + 1}", price, 1.0 + i) for i, price in enumerate(targets)),
        horizon_bars=horizon,
        reason_codes=("TEST",),
    )


def test_gap_through_stop_fills_at_open_not_at_stop():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 99, 100, 98, 99),
        ]
    )
    result = run_signal(signal(), bars, NQ)
    assert result is not None
    assert result.outcome == "STOP"
    assert result.exit_price == 99
    assert result.points == pytest.approx(-0.25)


def test_gap_beyond_first_target_is_skipped():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 107, 108, 106.5, 107.5),
        ]
    )
    assert run_signal(signal(), bars, NQ) is None


def test_ambiguous_bar_uses_stop_first():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 107, 99, 105),
        ]
    )
    result = run_signal(signal(), bars, NQ)
    assert result is not None
    assert result.outcome == "STOP"
    assert result.exit_price == 100


def test_max_one_target_per_bar():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 110, 102, 109),
            bar(START + timedelta(minutes=10), 107, 108, 106, 108),
        ]
    )
    result = run_signal(signal(horizon=1), bars, NQ, BacktestConfig(max_targets_per_bar=1))
    assert result is not None
    assert result.target_fills == ("TP1",)
    assert result.outcome == "TP_THEN_TIMEOUT"
    assert result.points == pytest.approx(3.75)
    assert result.costs == pytest.approx(17.5)


def test_timeout_exits_at_horizon_close():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 104, 102, 104),
            bar(START + timedelta(minutes=10), 104, 105, 103, 105),
            bar(START + timedelta(minutes=15), 105, 106, 104, 106),
        ]
    )
    result = run_signal(signal(targets=(110.0,), horizon=2), bars, NQ)
    assert result is not None
    assert result.outcome == "TIMEOUT"
    assert result.exit_price == 106
    assert result.bars_held == 2


def test_costs_and_contract_sizing_nq_vs_es():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 106.5, 102, 106),
        ]
    )
    nq = run_signal(signal(targets=(106.0,), horizon=1), bars, NQ)
    es = run_signal(signal(targets=(106.0,), horizon=1), bars, ES)
    assert nq is not None and es is not None
    assert nq.points == pytest.approx(2.75)
    assert nq.costs == pytest.approx(15.0)
    assert nq.dollars == pytest.approx(40.0)
    assert es.costs == pytest.approx(30.0)
    assert es.dollars == pytest.approx(107.5)


def test_partial_exit_charges_three_commissions():
    bars = pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, 106.5, 102, 106),
            bar(START + timedelta(minutes=10), 106, 109.5, 105, 109),
        ]
    )
    result = run_signal(signal(), bars, NQ)
    assert result is not None
    assert result.target_fills == ("TP1", "TP2")
    assert result.costs == pytest.approx(17.5)
    assert result.dollars == pytest.approx(67.5)


def test_config_rejects_unsupported_ambiguity_and_bad_contracts():
    bars = pd.DataFrame([bar(START, 103, 103, 102.5, 103)])
    with pytest.raises(ValueError):
        run_signal(signal(), bars, NQ, BacktestConfig(ambiguous_policy="TARGET_FIRST"))
    with pytest.raises(ValueError):
        run_signal(signal(), bars, NQ, BacktestConfig(contracts=0))
