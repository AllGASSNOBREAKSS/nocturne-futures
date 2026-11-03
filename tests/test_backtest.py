from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.backtest import BacktestConfig, BacktestReport, run_signal, split_sessions
from nocturne.instruments import get_instrument
from nocturne.strategies.base import Signal, TargetSpec

UTC = timezone.utc
NQ = get_instrument("NQ")
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


def signal(stop=100.0, entry=103.0):
    return Signal(
        strategy_id="test",
        strategy_version="0.1",
        instrument_id="NQ",
        asof=START + timedelta(minutes=5),
        side="LONG",
        entry_low=entry,
        entry_high=entry,
        stop=stop,
        targets=(
            TargetSpec("TP1", entry + (entry - stop), 1.0),
            TargetSpec("TP2", entry + 2 * (entry - stop), 2.0),
        ),
        horizon_bars=6,
        reason_codes=("TEST",),
    )


def bars_after_entry(high1=106.5, low1=102.5, high2=109.5, low2=104.5):
    return pd.DataFrame(
        [
            bar(START, 103, 103, 102.5, 103),
            bar(START + timedelta(minutes=5), 103, high1, low1, 105),
            bar(START + timedelta(minutes=10), 105, high2, low2, 109),
            bar(START + timedelta(minutes=15), 109, 109.5, 108, 109),
        ]
    )


def test_targets_fill_and_net_dollars():
    result = run_signal(signal(), bars_after_entry(), NQ)
    assert result is not None
    assert result.outcome == "TP2"
    assert result.target_fills == ("TP1", "TP2")
    assert result.points > 4
    assert result.dollars > 0


def test_stop_hit_is_negative():
    result = run_signal(signal(), bars_after_entry(high1=104, low1=99, high2=104, low2=98), NQ)
    assert result is not None
    assert result.outcome == "STOP"
    assert result.dollars < 0


def test_ambiguous_bar_uses_stop_first():
    result = run_signal(signal(), bars_after_entry(high1=107, low1=99, high2=108, low2=100), NQ)
    assert result is not None
    assert result.outcome == "STOP"


def test_costs_reduce_net_dollars():
    free = run_signal(signal(), bars_after_entry(), NQ, BacktestConfig(commission_per_contract=0, slippage_ticks=0))
    costly = run_signal(signal(), bars_after_entry(), NQ, BacktestConfig(commission_per_contract=2.5, slippage_ticks=1))
    assert free is not None and costly is not None
    assert costly.dollars < free.dollars


def test_report_summary():
    report = BacktestReport(trades=[run_signal(signal(), bars_after_entry(), NQ)])
    summary = report.summary()
    assert summary["trades"] == 1
    assert summary["wins"] == 1
    assert summary["net_dollars"] > 0


def test_split_sessions_is_chronological():
    days = [date(2026, 11, 2) + timedelta(days=i) for i in range(10)]
    train, test = split_sessions(days, 0.6)
    assert len(train) == 6
    assert len(test) == 4
    assert max(train) < min(test)
