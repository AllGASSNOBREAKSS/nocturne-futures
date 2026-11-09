"""Cached intraday bars for reproducible backtests."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

from ..adapters.yahoo import bars_frame, fetch_events
from ..instruments import InstrumentSpec, get_instrument
from ..market_clock import session_date

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "market" / "intraday"


def add_session_column(bars: pd.DataFrame, spec: InstrumentSpec) -> pd.DataFrame:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    # Same rule as market_clock.session_date, evaluated once per distinct
    # (ET date, after-18:00) pair instead of once per bar (identical output).
    et = frame["timestamp"].dt.tz_convert("America/New_York")
    after = et.dt.hour >= 18
    keys = pd.DataFrame({"day": et.dt.date, "after": after})
    lookup = {}
    for day, late in keys.drop_duplicates().itertuples(index=False):
        probe = pd.Timestamp(day).tz_localize("America/New_York") + pd.Timedelta(hours=19 if late else 12)
        lookup[(day, late)] = session_date(probe.to_pydatetime(), spec)
    frame["session"] = [lookup[k] for k in zip(keys["day"], keys["after"])]
    return frame


def load_intraday(
    instrument: str,
    interval: str = "5m",
    force: bool = False,
) -> tuple[pd.DataFrame, dict]:
    spec = get_instrument(instrument)
    if not spec.yahoo_symbol:
        raise ValueError(f"no public bar symbol for {instrument}")
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{instrument.upper()}_{interval}.csv"
    meta_path = CACHE / f"{instrument.upper()}_{interval}.meta.json"

    if path.exists() and meta_path.exists() and not force:
        frame = pd.read_csv(path)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
        return frame, json.loads(meta_path.read_text(encoding="utf-8"))

    events = fetch_events(spec.yahoo_symbol, range_="60d", interval=interval)
    frame = bars_frame(events)
    if frame.empty:
        raise ValueError("no intraday bars returned")
    frame.to_csv(path, index=False)
    meta = {
        "instrument": instrument.upper(),
        "interval": interval,
        "rows": int(len(frame)),
        "first": str(frame["timestamp"].iloc[0]),
        "last": str(frame["timestamp"].iloc[-1]),
        "source": "yahoo_public_unofficial",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "fetched_at": pd.Timestamp.utcnow().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return frame, meta


def session_days(bars: pd.DataFrame, spec: InstrumentSpec) -> list[date]:
    frame = add_session_column(bars, spec)
    return sorted(frame["session"].unique())
