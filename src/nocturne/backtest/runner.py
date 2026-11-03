"""Run a strategy over cached intraday bars, session by session."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..auction.session import session_bars
from ..instruments import get_instrument
from ..strategies.opening_range import OpeningRangeBreakout
from .data import add_session_column, load_intraday
from .engine import BacktestConfig, BacktestReport, run_signal


def run_orb(
    instrument_id: str = "NQ",
    config: BacktestConfig | None = None,
    force: bool = False,
) -> tuple[dict, list[dict]]:
    spec = get_instrument(instrument_id)
    bars, meta = load_intraday(instrument_id, force=force)
    bars = add_session_column(bars, spec)
    strategy = OpeningRangeBreakout(ib_minutes=60, buffer_ticks=2)

    report = BacktestReport()
    for day, group in bars.groupby("session"):
        rth = session_bars(group, spec, "RTH", day)
        signals = strategy.signals(group, spec, day)
        for signal in signals:
            result = run_signal(signal, rth, spec, config)
            if result is not None:
                report.trades.append(result)

    summary = report.summary()
    summary["data"] = meta
    return summary, [asdict(trade) for trade in report.trades]


def save_report(root: Path, name: str, summary: dict, trades: list[dict]) -> Path:
    import json

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.json"
    path.write_text(
        json.dumps({"summary": summary, "trades": trades}, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path
