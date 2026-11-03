"""Build intermarket and premarket context artifacts from available data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .adapters.yahoo import bars_frame, fetch_events
from .instruments import get_instrument
from .intermarket import build_intermarket_state
from .market_clock import session_date
from .premarket import build_premarket_state

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[2]
FORECASTS = ROOT / "data" / "forecasts"


def _optional_daily(symbol: str) -> pd.DataFrame | None:
    try:
        events = fetch_events(symbol, range_="2y", interval="1d")
        frame = bars_frame(events)
        frame["date"] = pd.to_datetime(frame["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
        return frame[["date", "open", "high", "low", "close"]]
    except Exception:
        return None


def build_context(offline: bool = False) -> dict:
    from .pipeline import load_daily_csv

    es = load_daily_csv("ES")
    nq = load_daily_csv("NQ")
    vix_path = ROOT / "data" / "market" / "daily" / "VIX.csv"
    if not vix_path.exists():
        vix_path = ROOT / "data" / "studies" / "daily_15y" / "VIX.csv"
    vix = pd.read_csv(vix_path)
    vix["date"] = pd.to_datetime(vix["date"]).dt.strftime("%Y-%m-%d")

    zn = None if offline else _optional_daily("ZN=F")
    zb = None if offline else _optional_daily("ZB=F")

    state = build_intermarket_state(es, nq, vix=vix, zn=zn, zb=zb)
    FORECASTS.mkdir(parents=True, exist_ok=True)
    (FORECASTS / "intermarket.json").write_text(
        json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8"
    )

    premarket_payload: dict
    if offline:
        premarket_payload = {"state": None, "reason": "OFFLINE_MODE"}
    else:
        try:
            nq_15 = bars_frame(fetch_events("NQ=F", range_="5d", interval="15m"))
            es_15 = bars_frame(fetch_events("ES=F", range_="5d", interval="15m"))
            now = datetime.now(UTC)
            pre = build_premarket_state(
                nq_15,
                es_15,
                get_instrument("NQ"),
                get_instrument("ES"),
                session_date(now, get_instrument("NQ")),
                now,
                vix_level=state.vix_level,
            )
            premarket_payload = pre.to_dict()
        except Exception as exc:  # noqa: BLE001 - data gate
            premarket_payload = {"state": None, "reason": f"INTRADAY_FETCH_FAILED: {exc}"}

    (FORECASTS / "premarket.json").write_text(
        json.dumps(premarket_payload, indent=2) + "\n", encoding="utf-8"
    )
    return {"intermarket": state.to_dict(), "premarket": premarket_payload}
