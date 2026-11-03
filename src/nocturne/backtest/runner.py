"""Run a strategy over fetched intraday bars, session by session."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from ..adapters.yahoo import bars_frame, fetch_events
from ..instruments import get_instrument
from ..market_clock import session_date
from ..strategies.opening_range import OpeningRangeBreakout
from .engine import BacktestConfig, BacktestReport, run_signal


def run_orb(
    instrument_id: str = "NQ",
    days: int = 60,
    config: BacktestConfig | None = None,
) -> tuple[dict, list[dict]]:
    spec = get_instrument(instrument_id)
    if not spec.yahoo_symbol:
        raise ValueError(f"no public bar symbol for {instrument_id}")
    events = fetch_events(spec.yahoo_symbol, range_=f"{days}d", interval="5m")
    bars = bars_frame(events)
    if bars.empty:
        raise ValueError("no intraday bars returned")
    bars["session"] = [
        session_date(ts.to_pydatetime(), spec) for ts in bars["timestamp"]
    ]

    strategy = OpeningRangeBreakout(ib_minutes=60, buffer_ticks=2)
    report = BacktestReport()
    for day, group in bars.groupby("session"):
        signals = strategy.signals(group, spec, day)
        for signal in signals:
            result = run_signal(signal, group, spec, config)
            if result is not None:
                report.trades.append(result)
    return report.summary(), [asdict(trade) for trade in report.trades]


def save_report(root: Path, name: str, summary: dict, trades: list[dict]) -> Path:
    import json

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.json"
    path.write_text(
        json.dumps({"summary": summary, "trades": trades}, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path
