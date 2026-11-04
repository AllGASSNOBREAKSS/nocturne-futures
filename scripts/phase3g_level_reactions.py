"""Build the price-level interaction database from cached five-minute sessions."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.adapters.history import checksum
from nocturne.backtest.data import add_session_column, load_intraday
from nocturne.instruments import get_instrument
from nocturne.price_levels.engine import build_levels
from nocturne.research.level_reactions import LevelEventConfig, level_events, summarize_events
from nocturne.sessions import session_window_for

ROOT = Path(__file__).resolve().parents[1]
CONFIG = LevelEventConfig()


def atr(frame: pd.DataFrame, window: int = 14) -> float:
    previous = frame.close.shift(1)
    true_range = pd.concat([frame.high - frame.low, (frame.high - previous).abs(),
                            (frame.low - previous).abs()], axis=1).max(axis=1)
    value = true_range.rolling(window).mean().iloc[-1]
    return float(value) if np.isfinite(value) else float("nan")


def main():
    report = {"decision": "RESEARCH_ONLY", "holdout_scored": False,
              "protocol": "phase3g-level-reactions-v1",
              "config": CONFIG.__dict__,
              "event_definitions": {
                  "touched": "future bar range contains the level",
                  "acceptance": f"{CONFIG.accept_closes} consecutive closes beyond the level",
                  "rejection": f"adverse {CONFIG.reject_atr} ATR without {CONFIG.break_atr} ATR progress",
                  "break_through": f"{CONFIG.break_atr} ATR progress beyond the level",
                  "target_before_stop": f"{CONFIG.target_atr} ATR target vs {CONFIG.stop_atr} ATR stop from the touch"},
              "instruments": {}}
    for instrument in ("NQ", "ES"):
        bars, meta = load_intraday(instrument)
        spec = get_instrument(instrument)
        bars = add_session_column(bars, spec)
        days = sorted(bars.session.unique())
        development = days[:int(.8 * len(days))]
        frames = []
        for day in development:
            window = session_window_for(spec, "NEW_YORK", day)
            asof = window.start_utc + pd.Timedelta(minutes=60)
            session = bars[(bars.timestamp >= window.start_utc) & (bars.timestamp < window.end_utc)]
            if len(session) < 78:
                continue
            try:
                level_set = build_levels(bars, spec, day, asof)
            except Exception:  # insufficient history for a session
                continue
            value = atr(bars[bars.available_at <= asof])
            if not np.isfinite(value) or value <= 0:
                continue
            events = level_events(session, level_set.levels, asof, value, CONFIG)
            if not events.empty:
                events["day"] = str(day)
                events["instrument"] = instrument
                frames.append(events)
        if not frames:
            report["instruments"][instrument] = {"status": "NO_EVENTS"}
            continue
        data = pd.concat(frames, ignore_index=True)
        data["distance_bucket"] = pd.cut(data.distance_atr, [0, 1, 2, 4, 100],
                                         labels=["<1 ATR", "1-2 ATR", "2-4 ATR", ">4 ATR"])
        overall = summarize_events(data)
        by_type = {str(k): summarize_events(g) for k, g in data.groupby("level_type") if len(g) >= 40}
        by_bucket = {str(k): summarize_events(g) for k, g in data.groupby("distance_bucket", observed=True)}
        data.to_csv(ROOT / f"data/research/{instrument}_level_reactions_phase3g.csv", index=False)
        report["instruments"][instrument] = {
            "source": meta, "sessions": int(data.day.nunique()), "overall": overall,
            "by_level_type": by_type, "by_distance_bucket": by_bucket,
            "dataset_sha256": checksum(ROOT / f"data/research/{instrument}_level_reactions_phase3g.csv"),
            "limitations": ["level outcomes are correlated within a session",
                            "bar-extreme touches, not queue-position fills",
                            "ambiguous same-bar barriers excluded from target_before_stop"]}
        print(instrument, overall["rows"], overall["touched"],
              {k: v.get("touch_rate") for k, v in by_bucket.items()})
    (ROOT / "reports/phase3g_level_reactions.json").write_text(
        json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")


if __name__ == "__main__":
    main()
