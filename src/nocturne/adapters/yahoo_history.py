"""Long-range daily history from Yahoo's public chart endpoint.

Yahoo is unofficial and rate-limited. Daily bars are marked available at the next
UTC midnight, which is after the US close but conservative relative to the exact
close. Index levels, ETF prices and futures proxies are stored separately and
never merged into one price series.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .yahoo import USER_AGENT

UTC = timezone.utc
EPOCH_1900 = -2208988800
DEFAULT_SYMBOLS = {
    "^NDX": {"name": "Nasdaq-100 index", "kind": "index", "start": 1985},
    "^GSPC": {"name": "S&P 500 index", "kind": "index", "start": 1927},
    "^VIX": {"name": "CBOE VIX index (spot proxy)", "kind": "volatility_index", "start": 1990},
    "QQQ": {"name": "Invesco QQQ ETF", "kind": "etf", "start": 1999},
    "SPY": {"name": "SPDR S&P 500 ETF", "kind": "etf", "start": 1993},
    "^TNX": {"name": "10-year Treasury yield index (x10)", "kind": "rate_index", "start": 1962},
    "TLT": {"name": "iShares 20+ year Treasury ETF", "kind": "etf", "start": 2002},
    "NQ=F": {"name": "Nasdaq-100 futures continuous front month", "kind": "futures_proxy", "start": 1996},
    "ES=F": {"name": "S&P 500 futures continuous front month", "kind": "futures_proxy", "start": 1997},
}


def _frame(payload: dict, symbol: str) -> pd.DataFrame:
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise ValueError(f"no chart result for {symbol}")
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    rows = []
    for index, stamp in enumerate(timestamps):
        close = quote["close"][index]
        if close is None:
            continue
        start = pd.Timestamp(int(stamp), unit="s", tz="UTC")
        rows.append({
            "date": start.date().isoformat(),
            "timestamp": start,
            "available_at": pd.Timestamp(start.date() + timedelta(days=1), tz="UTC"),
            "open": quote["open"][index] if quote["open"][index] is not None else close,
            "high": quote["high"][index] if quote["high"][index] is not None else close,
            "low": quote["low"][index] if quote["low"][index] is not None else close,
            "close": close,
            "volume": quote["volume"][index] or 0,
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    if frame.date.duplicated().any():
        raise ValueError(f"duplicate dates for {symbol}")
    valid = ((frame.high >= frame[["open", "close", "low"]].max(axis=1))
             & (frame.low <= frame[["open", "close", "high"]].min(axis=1)))
    frame = frame[valid]
    if frame.empty:
        raise ValueError(f"no valid bars for {symbol}")
    return frame.sort_values("date").reset_index(drop=True)


def _fetch_daily(symbol: str, retries: int = 4, pause: float = 2.0) -> dict:
    """Daily bars via explicit period bounds.

    ``range=max`` is downsampled by Yahoo to monthly bars, so it must not be used
    for daily history.
    """
    import requests
    import time as _time

    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{requests.utils.quote(symbol)}?period1={EPOCH_1900}&period2="
        f"{int(datetime.now(UTC).timestamp())}&interval=1d&events=div%2Csplits"
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT,
                                                 "Accept": "application/json"}, timeout=45)
            response.raise_for_status()
            payload = response.json()
            granularity = payload.get("chart", {}).get("result", [{}])[0].get("meta", {}).get("dataGranularity")
            if granularity not in (None, "1d"):
                raise ValueError(f"unexpected granularity {granularity}")
            return payload
        except Exception as exc:  # noqa: BLE001 - adapter boundary
            last_error = exc
            _time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"Yahoo daily history failed for {symbol}: {last_error}")


def fetch_daily_history(symbol: str, root: Path, pause: float = 2.0) -> dict:
    root = Path(root)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "normalized").mkdir(exist_ok=True)
    (root / "manifests").mkdir(exist_ok=True)
    payload = _fetch_daily(symbol, pause=pause)
    frame = _frame(payload, symbol)
    if frame.empty:
        raise ValueError(f"empty history for {symbol}")
    requested = len(payload.get("chart", {}).get("result", [{}])[0].get("timestamp") or [])
    dropped_invalid = requested - len(frame)
    raw = json.dumps(payload, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    (root / "raw" / f"{symbol.replace('^', 'IDX_').replace('=', '_')}_{digest}.json").write_bytes(raw)
    destination = root / "normalized" / f"{symbol.replace('^', 'IDX_').replace('=', '_')}.csv"
    frame.to_csv(destination, index=False, lineterminator="\n")
    meta = DEFAULT_SYMBOLS.get(symbol, {})
    gaps = pd.to_datetime(frame.date).diff().dt.days
    manifest = {
        "symbol": symbol, "name": meta.get("name"), "kind": meta.get("kind", "unknown"),
        "provider": "yahoo_public_unofficial", "frequency": "1d",
        "license_scope": "public_research_unofficial",
        "raw_sha256": digest, "normalized_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "rows": len(frame), "first": frame.date.iloc[0], "last": frame.date.iloc[-1],
        "span_years": round((pd.Timestamp(frame.date.iloc[-1]) - pd.Timestamp(frame.date.iloc[0])).days / 365.25, 2),
        "zero_volume_rows": int((frame.volume == 0).sum()),
        "dropped_invalid_or_missing_bars": int(dropped_invalid),
        "gap_days_median": float(gaps.median()) if len(gaps.dropna()) else None,
        "gaps_over_5_days": int((gaps > 5).sum()),
        "received_at": datetime.now(UTC).isoformat(),
        "availability": "next UTC midnight after the session date",
        "known_limitations": [
            "unofficial endpoint; not an exchange feed",
            "index levels are not tradable",
            "continuous futures proxies have unverified roll mapping",
            "adjusted vs unadjusted prices not distinguished by this adapter",
        ],
    }
    (root / "manifests" / f"{destination.stem}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_history(root: Path, symbol: str) -> pd.DataFrame:
    name = symbol.replace("^", "IDX_").replace("=", "_")
    frame = pd.read_csv(Path(root) / "normalized" / f"{name}.csv")
    for column in ("timestamp", "available_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame
