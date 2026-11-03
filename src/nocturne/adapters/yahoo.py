"""Yahoo Finance bar adapter.

Yahoo is a public, unofficial endpoint. It is used for bar-level context only.
It is not an exchange feed and must never be presented as tick/DOM data.
"""

from __future__ import annotations

import time as _time
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests

from ..contracts import EventType, MarketEvent, Quality
from ..instruments import instrument_for_yahoo_symbol

UTC = timezone.utc
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_INTERVAL_SECONDS = {
    "1m": 60,
    "2m": 120,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "60m": 3600,
    "1h": 3600,
    "1d": 86400,
    "1wk": 604800,
}


def fetch_chart(
    symbol: str,
    range_: str = "1mo",
    interval: str = "1d",
    retries: int = 4,
    pause: float = 1.5,
) -> dict[str, Any]:
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol)}"
        f"?range={range_}&interval={interval}"
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            last_error = exc
            _time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"Yahoo fetch failed for {symbol}: {last_error}")


def events_from_chart(
    payload: dict[str, Any],
    symbol: str,
    interval: str,
    received_at: datetime | None = None,
) -> list[MarketEvent]:
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise ValueError("chart payload has no result")

    spec = instrument_for_yahoo_symbol(symbol)
    instrument_id = spec.instrument_id if spec else symbol
    duration = timedelta(seconds=_INTERVAL_SECONDS.get(interval, 86400))
    received = received_at or datetime.now(UTC)

    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    events: list[MarketEvent] = []

    for index, stamp in enumerate(timestamps):
        close = quote["close"][index]
        if close is None:
            continue
        bar_start = datetime.fromtimestamp(stamp, UTC)
        bar_end = bar_start + duration
        open_ = quote["open"][index] if quote["open"][index] is not None else close
        high = quote["high"][index] if quote["high"][index] is not None else close
        low = quote["low"][index] if quote["low"][index] is not None else close
        volume = quote["volume"][index] or 0

        events.append(
            MarketEvent(
                event_id=f"yahoo:{symbol}:{interval}:{stamp}",
                source="yahoo",
                instrument_id=instrument_id,
                contract_id=None,
                venue="YAHOO",
                event_type=EventType.BAR,
                event_time_utc=bar_start,
                available_at_utc=bar_end,
                received_at_utc=received,
                source_sequence=index,
                license_scope="yahoo_public_unofficial",
                payload={
                    "symbol": symbol,
                    "interval": interval,
                    "open": float(open_),
                    "high": float(high),
                    "low": float(low),
                    "close": float(close),
                    "volume": float(volume),
                    "bar_start_utc": bar_start.isoformat(),
                    "bar_end_utc": bar_end.isoformat(),
                },
                quality=Quality(coverage=1.0),
            )
        )
    return events


def fetch_events(
    symbol: str,
    range_: str = "1mo",
    interval: str = "1d",
) -> list[MarketEvent]:
    payload = fetch_chart(symbol, range_=range_, interval=interval)
    return events_from_chart(payload, symbol=symbol, interval=interval)


def bars_frame(events: list[MarketEvent]) -> pd.DataFrame:
    rows = []
    for event in events:
        if event.event_type != EventType.BAR:
            continue
        p = event.payload
        rows.append(
            {
                "timestamp": event.event_time_utc,
                "available_at": event.available_at_utc,
                "open": p["open"],
                "high": p["high"],
                "low": p["low"],
                "close": p["close"],
                "volume": p["volume"],
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("timestamp").reset_index(drop=True)
