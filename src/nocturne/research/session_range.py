"""Empirical session-range quantiles from complete five-minute windows.

Only full grids are used. Expanding quantiles mean every forecast is built from
strictly earlier sessions. Sample sizes are small; results are descriptive.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..instruments import InstrumentSpec
from ..market_clock import is_trading_day
from ..sessions import session_window_for


def session_ranges(bars: pd.DataFrame, spec: InstrumentSpec, session: str) -> pd.DataFrame:
    frame = bars.copy()
    for column in ("timestamp", "available_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    rows = []
    for day in sorted(frame.session.unique()):
        if not is_trading_day(day):
            continue
        window = session_window_for(spec, session, day)
        sample = frame[(frame.timestamp >= window.start_utc) & (frame.timestamp < window.end_utc)]
        grid = pd.date_range(window.start_utc, window.end_utc, freq="5min", inclusive="left")
        if not pd.DatetimeIndex(sample.timestamp).equals(grid):
            continue
        rows.append({"day": str(day), "range": float(sample.high.max() - sample.low.min()),
                     "close": float(sample.close.iloc[-1]), "bars": len(sample)})
    return pd.DataFrame(rows).sort_values("day").reset_index(drop=True)


def expanding_quantile_backtest(ranges: pd.DataFrame, quantiles=(.5, .8, .9), min_history: int = 20):
    """One-step-ahead expanding empirical quantiles with no same-day peeking."""
    result = {q: {"loss": [], "covered": [], "predicted": [], "actual": [], "day": []} for q in quantiles}
    values = ranges.range.to_numpy()
    days = ranges.day.to_numpy()
    for index in range(min_history, len(ranges)):
        history = values[:index]
        actual = values[index]
        for q in quantiles:
            predicted = float(np.quantile(history, q))
            result[q]["loss"].append(max(q * (actual - predicted), (q - 1) * (actual - predicted)))
            result[q]["covered"].append(actual <= predicted)
            result[q]["predicted"].append(predicted)
            result[q]["actual"].append(actual)
            result[q]["day"].append(days[index])
    summary = {}
    for q, values_ in result.items():
        if not values_["loss"]:
            summary[str(q)] = {"n": 0}
            continue
        summary[str(q)] = {"n": len(values_["loss"]),
                           "pinball_loss": float(np.mean(values_["loss"])),
                           "coverage": float(np.mean(values_["covered"])),
                           "median_predicted": float(np.median(values_["predicted"])),
                           "mean_actual": float(np.mean(values_["actual"])),
                           "rows": values_}
    return summary


def summarize(ranges: pd.DataFrame, min_history: int = 20) -> dict:
    if len(ranges) <= min_history:
        return {"status": "INSUFFICIENT_COMPLETE_SESSIONS", "complete_sessions": len(ranges)}
    backtest = expanding_quantile_backtest(ranges, min_history=min_history)
    return {"status": "RESEARCH_ONLY", "complete_sessions": len(ranges),
            "date_range": [ranges.day.min(), ranges.day.max()],
            "unconditional": {str(q): float(np.quantile(ranges.range, q)) for q in (.5, .8, .9)},
            "expanding_backtest": {q: {k: v for k, v in entry.items() if k != "rows"}
                                   for q, entry in backtest.items()},
            "raw_range_quantiles": {str(q): float(np.quantile(ranges.range, q)) for q in (.5, .8, .9)},
            "event": "full_session_high_minus_low"}


def calibration_payload(bars, spec, sessions=("ASIA", "LONDON", "NEW_YORK")) -> dict:
    """Compact per-session coverage evidence for forecast provenance."""
    payload = {"method": "expanding_empirical_quantiles", "min_history": 20, "sessions": {}}
    for session in sessions:
        summary = summarize(session_ranges(bars, spec, session))
        if summary.get("status") != "RESEARCH_ONLY":
            payload["sessions"][session] = {"status": summary["status"],
                                            "complete_sessions": summary.get("complete_sessions", 0)}
            continue
        payload["sessions"][session] = {
            "status": "RESEARCH_ONLY",
            "complete_sessions": summary["complete_sessions"],
            "date_range": summary["date_range"],
            "coverage": {q: entry.get("coverage") for q, entry in summary["expanding_backtest"].items()},
            "n": {q: entry.get("n") for q, entry in summary["expanding_backtest"].items()},
        }
    return payload


def load_calibration(root):
    import json
    from pathlib import Path
    path = Path(root) / "session_range_calibration.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
