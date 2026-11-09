"""Stored market data, derived intervals, reference levels and regime context.

Sources are the checksummed free archive (Yahoo continuous front-month,
research-grade) plus any Databento datasets ingested later under
data/licensed/databento. Data is historical/delayed, never real-time.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from ..auction.volume_profile import build_bar_approximation
from ..collector.store import Archive
from ..instruments import get_instrument
from . import ROOT
from .indicators import atr, globex_session, session_vwap, sma

FREE = ROOT / "data/history/free"
ROOTS = ("NQ", "ES")
NATIVE = {"1m": "1m", "5m": "5m", "1h": "60m", "1d": "1d"}
DERIVED = {"15m": ("5m", "15min"), "4h": ("60m", "4h"), "1w": ("1d", "W-FRI")}
SESSIONS_ET = {"ASIA": (18, 3), "LONDON": (3, 9), "NEW_YORK": (9, 16)}  # hourly-aligned approximations


OPERATIONAL = ROOT / "data/research/free"


class CompositeArchive:
    """Operational refreshes (ignored) override the committed snapshot per dataset."""

    def __init__(self):
        self.layers = [Archive(OPERATIONAL), Archive(FREE)]

    def latest(self, source, dataset):
        for layer in self.layers:
            entry = layer.latest(source, dataset) if (layer.root / source / dataset).exists() else None
            if entry:
                return {**entry, "layer": "operational" if layer.root == OPERATIONAL else "committed"}
        return None

    def load(self, source, dataset, entry=None):
        for layer in self.layers:
            if (layer.root / source / dataset).exists() and layer.latest(source, dataset):
                return layer.load(source, dataset)
        return None


def archive():
    return CompositeArchive()


def datasets():
    out = []
    a = archive()
    for root in ROOTS:
        for interval, native in NATIVE.items():
            entry = a.latest("yahoo_futures", f"{root}_{native}")
            if entry:
                out.append({"id": f"yahoo_futures/{root}_{native}", "root": root, "interval": interval, "rows": entry["rows"],
                            "first": entry.get("first"), "last": entry.get("last"), "retrieved_at": entry["retrieved_at"],
                            "normalized_sha256": entry["normalized_sha256"], "source": "Yahoo continuous front-month (unadjusted)",
                            "credibility": entry.get("credibility"), "status": "AVAILABLE", "license": "research-grade public, not for redistribution"})
    licensed = ROOT / "data/licensed/databento/store"
    out.append({"id": "databento/GLBX.MDP3", "root": "NQ,ES", "interval": "1m", "rows": sum(1 for _ in licensed.rglob("*.csv")) if licensed.exists() else 0,
                "source": "Databento GLBX.MDP3 raw contracts", "status": "BLOCKED_KEY_ROTATION_AND_CREDIT_VERIFICATION",
                "license": "licensed; private display only"})
    return out


@lru_cache(maxsize=32)
def _load(root, native, sha):
    frame = archive().load("yahoo_futures", f"{root}_{native}")
    frame = frame[frame.ohlc_consistent.astype(bool)]
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    return frame[["timestamp", "open", "high", "low", "close", "volume"]].sort_values("timestamp").reset_index(drop=True)


def bars(root, interval, start=None, end=None, limit=5000):
    if root not in ROOTS:
        raise ValueError("unsupported instrument")
    if interval in NATIVE:
        native, rule = NATIVE[interval], None
    elif interval in DERIVED:
        native, rule = DERIVED[interval]
    else:
        raise ValueError("unsupported interval")
    entry = archive().latest("yahoo_futures", f"{root}_{native}")
    if entry is None:
        raise ValueError("dataset not collected")
    frame = _load(root, native, entry["normalized_sha256"])
    if rule:
        frame = (frame.set_index("timestamp").resample(rule, label="left", closed="left")
                 .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
                 .dropna().reset_index())
    if start:
        frame = frame[frame.timestamp >= pd.Timestamp(start, tz="UTC")]
    if end:
        frame = frame[frame.timestamp < pd.Timestamp(end, tz="UTC")]
    frame = frame.tail(limit).reset_index(drop=True)
    # A bar is knowable only once it has closed: never at its start time.
    step = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D", "1w": "7D"}[interval]
    frame["available_at"] = frame.timestamp + pd.Timedelta(step)
    return frame, {"dataset": f"yahoo_futures/{root}_{native}", "normalized_sha256": entry["normalized_sha256"],
                   "retrieved_at": entry["retrieved_at"], "derived_rule": rule,
                   "freshness": "HISTORICAL_DELAYED_NOT_REALTIME"}


def _round(x, tick):
    return None if x is None or not np.isfinite(x) else round(round(x / tick) * tick, 2)


def levels(root):
    """Reference levels for the latest completed session from stored bars."""
    spec = get_instrument(root)
    daily, _ = bars(root, "1d", limit=400)
    five, meta = bars(root, "5m", limit=20000)
    five["session"] = globex_session(five.timestamp)
    last_session = five.session.iloc[-1]
    sessions = sorted(five.session.unique())
    prior = sessions[-2] if len(sessions) > 1 else last_session
    cur = five[five.session == last_session]
    prv = five[five.session == prior]
    et = cur.timestamp.dt.tz_convert("America/New_York")
    overnight = cur[(et.dt.hour >= 18) | (et.dt.hour < 9) | ((et.dt.hour == 9) & (et.dt.minute < 30))]
    rth = cur[((et.dt.hour == 9) & (et.dt.minute >= 30)) | ((et.dt.hour > 9) & (et.dt.hour < 16))]
    rth_et = rth.timestamp.dt.tz_convert("America/New_York")
    opening = rth[rth_et < rth_et.min() + pd.Timedelta(minutes=30)] if len(rth) else rth
    initial = rth[rth_et < rth_et.min() + pd.Timedelta(minutes=60)] if len(rth) else rth
    items = []

    def add(name, value, kind, basis):
        if value is not None and np.isfinite(value):
            items.append({"name": name, "price": _round(float(value), spec.tick_size), "kind": kind, "basis": basis})

    add("Prior session high", prv.high.max(), "reference", "5m bars")
    add("Prior session low", prv.low.min(), "reference", "5m bars")
    add("Prior session close", prv.close.iloc[-1] if len(prv) else None, "reference", "5m bars")
    add("Overnight high", overnight.high.max() if len(overnight) else None, "session", "18:00-09:30 ET")
    add("Overnight low", overnight.low.min() if len(overnight) else None, "session", "18:00-09:30 ET")
    add("Opening range high (30m)", opening.high.max() if len(opening) else None, "session", "RTH first 30m")
    add("Opening range low (30m)", opening.low.min() if len(opening) else None, "session", "RTH first 30m")
    add("Initial balance high", initial.high.max() if len(initial) else None, "session", "RTH first 60m")
    add("Initial balance low", initial.low.min() if len(initial) else None, "session", "RTH first 60m")
    vw = session_vwap(cur.reset_index(drop=True))
    add("Session VWAP", vw.iloc[-1] if len(vw) else None, "auction", "typical-price bar approximation")
    week = daily[daily.timestamp >= daily.timestamp.iloc[-1] - pd.Timedelta(days=7)]
    add("Prior 5-session high", week.high.max(), "reference", "daily")
    add("Prior 5-session low", week.low.min(), "reference", "daily")
    month = daily.tail(21)
    add("21-session high", month.high.max(), "reference", "daily")
    add("21-session low", month.low.min(), "reference", "daily")
    profile_src = prv if len(prv) else cur
    try:
        frame = profile_src.rename(columns={}).assign(available_at=profile_src.timestamp + pd.Timedelta(minutes=5))
        profile = build_bar_approximation(frame, root, spec.tick_size, session_type="ETH", bin_ticks=8 if root == "NQ" else 2)
        add("Prior POC", profile.poc_price, "auction", "BAR_APPROXIMATION (not traded volume-at-price)")
        add("Prior VAH", profile.vah_price, "auction", "BAR_APPROXIMATION")
        add("Prior VAL", profile.val_price, "auction", "BAR_APPROXIMATION")
    except (ValueError, KeyError):
        pass
    last = five.iloc[-1]
    return {"root": root, "session": str(last_session), "as_of": str(last.timestamp), "last_price": float(last.close),
            "levels": sorted(items, key=lambda x: -x["price"]), "data": meta,
            "warning": "Levels derive from research-grade continuous bars; profile values approximate volume-at-price from OHLCV."}


def regime(root):
    daily, meta = bars(root, "1d", limit=600)
    d = daily.copy()
    d["atr20"] = atr(d, 20)
    d["range"] = d.high - d.low
    d["sma50"], d["sma200"] = sma(d.close, 50), sma(d.close, 200)
    last = d.iloc[-1]
    pct = float((d["range"].tail(250) <= last["range"]).mean())
    trend = ("UPTREND" if last.close > last.sma50 > last.sma200 else "DOWNTREND" if last.close < last.sma50 < last.sma200 else "MIXED")
    compression = bool(d["range"].tail(5).mean() < 0.7 * last.atr20)
    expansion = bool(last["range"] > 1.5 * last.atr20)
    vix = archive().load("fred", "VIXCLS").tail(1)
    return {"root": root, "as_of": str(last.timestamp), "close": float(last.close), "atr20": float(last.atr20),
            "last_range": float(last["range"]), "range_percentile_250": round(pct, 3), "trend": trend,
            "state": "EXPANSION" if expansion else "COMPRESSION" if compression else "NORMAL",
            "sma50": float(last.sma50), "sma200": float(last.sma200),
            "vix": {"value": float(vix.value.iloc[0]), "date": vix.date.iloc[0]} if len(vix) else None,
            "method": "rule-based descriptive regime from daily bars; not a validated forecast", "data": meta}


def session_ranges(root):
    """Asia/London/New York high-low ranges per Globex session from hourly bars."""
    hourly, meta = bars(root, "1h", limit=100000)
    et = hourly.timestamp.dt.tz_convert("America/New_York")
    hourly = hourly.assign(session_date=globex_session(hourly.timestamp), hour=et.dt.hour)
    rows = []
    for name, (start, end) in SESSIONS_ET.items():
        mask = (hourly.hour >= start) | (hourly.hour < end) if start > end else (hourly.hour >= start) & (hourly.hour < end)
        g = hourly[mask].groupby("session_date").agg(high=("high", "max"), low=("low", "min"), n=("open", "size"),
                                                      last=("timestamp", "max"))
        expected = (24 - start + end) if start > end else end - start
        g = g[g.n >= expected - 1]
        g["range"] = g.high - g.low
        g["session"] = name
        rows.append(g.reset_index())
    return pd.concat(rows, ignore_index=True), meta


def json_safe(value):
    """Strict JSON: NaN/inf become null so responses never carry invalid numbers."""
    def clean(v):
        if isinstance(v, float):
            return v if np.isfinite(v) else None
        if isinstance(v, dict):
            return {str(k): clean(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [clean(x) for x in v]
        if isinstance(v, (np.floating,)):
            return clean(float(v))
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        return v
    return clean(json.loads(json.dumps(value, default=str)))
