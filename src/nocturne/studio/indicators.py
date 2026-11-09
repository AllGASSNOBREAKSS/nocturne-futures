"""Causal indicator library. Every value at bar t uses bars <= t only.

Signals evaluated on a bar's indicators are acted on at the NEXT bar open by
the backtest engine, so no indicator can see the bar it trades on.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GLOBEX_OPEN_HOUR_ET = 18


def sma(close, n=20):
    return close.rolling(n, min_periods=n).mean()


def ema(close, n=20):
    return close.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def macd(close, fast=12, slow=26, signal=9):
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, sig, line - sig


def true_range(frame):
    prev = frame.close.shift(1)
    return pd.concat([frame.high - frame.low, (frame.high - prev).abs(), (frame.low - prev).abs()], axis=1).max(axis=1)


def atr(frame, n=14):
    return true_range(frame).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(frame, n=14):
    up, down = frame.high.diff(), -frame.low.diff()
    plus = np.where((up > down) & (up > 0), up, 0.0)
    minus = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(frame).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    pdi = 100 * pd.Series(plus, index=frame.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / tr
    mdi = 100 * pd.Series(minus, index=frame.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / tr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def bollinger(close, n=20, k=2.0):
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return mid, mid + k * sd, mid - k * sd


def globex_session(timestamps):
    """Trading date of each bar: Globex sessions open 18:00 ET the prior day."""
    et = pd.to_datetime(timestamps, utc=True).dt.tz_convert("America/New_York")
    return (et + pd.Timedelta(hours=24 - GLOBEX_OPEN_HOUR_ET)).dt.date


def session_vwap(frame):
    """Developing Globex-session VWAP using typical price (bar approximation)."""
    session = globex_session(frame.timestamp)
    typical = (frame.high + frame.low + frame.close) / 3
    pv = (typical * frame.volume).groupby(session).cumsum()
    vol = frame.volume.groupby(session).cumsum()
    return (pv / vol.replace(0, np.nan)).rename("vwap")


def swing_points(frame, n=3):
    """Pivot highs/lows confirmed n bars later; the value appears at confirmation."""
    window = 2 * n + 1
    high_pivot = frame.high.rolling(window, center=True).max() == frame.high
    low_pivot = frame.low.rolling(window, center=True).min() == frame.low
    swing_high = frame.high.where(high_pivot).shift(n).ffill()
    swing_low = frame.low.where(low_pivot).shift(n).ffill()
    return swing_high, swing_low


CATALOG = {
    "close": {"label": "Close", "params": {}, "panel": "price"},
    "sma": {"label": "Simple moving average", "params": {"n": [5, 400, 20]}, "panel": "price"},
    "ema": {"label": "Exponential moving average", "params": {"n": [5, 400, 20]}, "panel": "price"},
    "vwap": {"label": "Session VWAP (bar approximation)", "params": {}, "panel": "price"},
    "bb_upper": {"label": "Bollinger upper", "params": {"n": [5, 200, 20], "k": [1, 4, 2]}, "panel": "price"},
    "bb_lower": {"label": "Bollinger lower", "params": {"n": [5, 200, 20], "k": [1, 4, 2]}, "panel": "price"},
    "swing_high": {"label": "Last confirmed swing high", "params": {"n": [2, 20, 3]}, "panel": "price"},
    "swing_low": {"label": "Last confirmed swing low", "params": {"n": [2, 20, 3]}, "panel": "price"},
    "rsi": {"label": "RSI", "params": {"n": [2, 100, 14]}, "panel": "oscillator"},
    "macd": {"label": "MACD line", "params": {"fast": [2, 50, 12], "slow": [5, 100, 26], "signal": [2, 50, 9]}, "panel": "oscillator"},
    "macd_signal": {"label": "MACD signal", "params": {"fast": [2, 50, 12], "slow": [5, 100, 26], "signal": [2, 50, 9]}, "panel": "oscillator"},
    "macd_hist": {"label": "MACD histogram", "params": {"fast": [2, 50, 12], "slow": [5, 100, 26], "signal": [2, 50, 9]}, "panel": "oscillator"},
    "adx": {"label": "ADX", "params": {"n": [5, 100, 14]}, "panel": "oscillator"},
    "atr": {"label": "ATR (points)", "params": {"n": [5, 100, 14]}, "panel": "oscillator"},
    "volume": {"label": "Volume", "params": {}, "panel": "volume"},
}
UNAVAILABLE = {
    "cvd": "Cumulative volume delta requires authentic trade aggressor data (FUTURES_DATA_BLOCKED)",
    "bid_ask_imbalance": "Requires authentic top-of-book quotes (FUTURES_DATA_BLOCKED)",
    "footprint": "Requires trades at price with aggressor side (FUTURES_DATA_BLOCKED)",
    "depth_imbalance": "Requires market-by-price depth (FUTURES_DATA_BLOCKED)",
}


def compute(frame, name, params=None):
    params = params or {}
    if name not in CATALOG:
        raise ValueError(f"unsupported indicator {name!r}")
    for key, value in params.items():
        bounds = CATALOG[name]["params"].get(key)
        if bounds is None or not bounds[0] <= float(value) <= bounds[1]:
            raise ValueError(f"invalid parameter {key}={value} for {name}")
    p = {k: v[2] for k, v in CATALOG[name]["params"].items()} | params
    c = frame.close
    if name == "close":
        return c
    if name == "volume":
        return frame.volume
    if name == "sma":
        return sma(c, int(p["n"]))
    if name == "ema":
        return ema(c, int(p["n"]))
    if name == "vwap":
        return session_vwap(frame)
    if name in ("bb_upper", "bb_lower"):
        _, upper, lower = bollinger(c, int(p["n"]), float(p["k"]))
        return upper if name == "bb_upper" else lower
    if name in ("swing_high", "swing_low"):
        high, low = swing_points(frame, int(p["n"]))
        return high if name == "swing_high" else low
    if name == "rsi":
        return rsi(c, int(p["n"]))
    if name.startswith("macd"):
        line, sig, hist = macd(c, int(p["fast"]), int(p["slow"]), int(p["signal"]))
        return {"macd": line, "macd_signal": sig, "macd_hist": hist}[name]
    if name == "adx":
        return adx(frame, int(p["n"]))
    if name == "atr":
        return atr(frame, int(p["n"]))
    raise ValueError(name)
