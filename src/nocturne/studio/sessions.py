"""Session level engine shared by the historical touch study and the live screen.

All times are America/New_York. A Globex session D runs 18:00 (D-1) -> 17:00 (D):
  Asia 18:00-03:00 · London 03:00-09:30 · New York 09:30-16:00.
`levels_at(...)` uses only bars that closed at or before the cutoff, so the same code is
point-in-time for backtests and live use.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ET = "America/New_York"
ASIA, LONDON, NY_OPEN, NY_CLOSE = (18 * 60, 3 * 60, 9 * 60 + 30, 16 * 60)
CUTOFFS = {"london": 3 * 60, "ny_open": 9 * 60 + 30, "post_ib": 10 * 60 + 30, "midday": 12 * 60, "afternoon": 14 * 60}
CUTOFF_LABEL = {"london": "03:00 ET (London open)", "ny_open": "09:30 ET (NY open)", "post_ib": "10:30 ET (after initial balance)",
                "midday": "12:00 ET (midday)", "afternoon": "14:00 ET (afternoon)"}

LEVEL_NAMES = {
    "PDH": "Prior day high", "PDL": "Prior day low", "PDC": "Prior settle", "PD_VWAP": "Prior day VWAP",
    "PD_POC": "Prior POC", "PD_VAH": "Prior value high", "PD_VAL": "Prior value low",
    "PRTH_H": "Prior NY high", "PRTH_L": "Prior NY low",
    "ASIA_H": "Asia high", "ASIA_L": "Asia low", "LON_H": "London high", "LON_L": "London low",
    "VWAP": "VWAP", "VWAP_U1": "VWAP +1σ", "VWAP_L1": "VWAP −1σ", "VWAP_U2": "VWAP +2σ", "VWAP_L2": "VWAP −2σ",
    "ORB15_H": "15m opening range high", "ORB15_L": "15m opening range low",
    "ORB30_H": "30m opening range high", "ORB30_L": "30m opening range low", "IB_H": "Initial balance high", "IB_L": "Initial balance low",
    "W5_H": "5-day high", "W5_L": "5-day low", "W20_H": "20-day high", "W20_L": "20-day low",
    "PIV_P": "Pivot", "PIV_R1": "Pivot R1", "PIV_S1": "Pivot S1", "PIV_R2": "Pivot R2", "PIV_S2": "Pivot S2",
    "EMA20D": "Daily EMA 20", "EMA50D": "Daily EMA 50", "SMA200D": "Daily SMA 200",
    "ML_UP50": "ML upside 50%", "ML_UP25": "ML upside 25%", "ML_DN50": "ML downside 50%", "ML_DN25": "ML downside 25%",
}
GROUP = {k: ("session" if k.split("_")[0] in ("ASIA", "LON", "ORB15", "ORB30", "IB", "PRTH") else
             "vwap" if k.startswith(("VWAP", "PD_VWAP")) else "auction" if k in ("PD_POC", "PD_VAH", "PD_VAL") else
             "indicator" if k.startswith(("PIV", "EMA", "SMA")) else "ml" if k.startswith("ML") else "reference") for k in LEVEL_NAMES}


def annotate(bars: pd.DataFrame) -> pd.DataFrame:
    """Add Globex session date and minutes-of-day (ET) columns."""
    t = pd.DatetimeIndex(bars.timestamp).tz_convert(ET)
    minutes = t.hour * 60 + t.minute
    session = (t + pd.to_timedelta(np.where(minutes >= ASIA, 1, 0), unit="D")).normalize().date
    out = bars.assign(session=session.astype(str), minute=minutes)
    return out[~((out.minute >= 17 * 60) & (out.minute < ASIA))]  # maintenance hour


def _in(m, start, end):
    """Minute-of-day mask for [start, end) where the window may wrap past midnight."""
    return (m >= start) & (m < end) if start < end else (m >= start) | (m < end)


def elapsed(minute, cutoff):
    """Has a bar *ending* at or before `cutoff` (both in session-relative minutes)?"""
    return _rel(minute) + 5 <= _rel(cutoff)


def _rel(m):
    m = np.asarray(m)
    return np.where(m >= ASIA, m - ASIA, m + 6 * 60)


def profile(bars, tick, bin_ticks):
    """Bar-approximation volume profile (uniform volume across each bar's range): POC, VAH, VAL."""
    if bars.empty:
        return None
    step = tick * bin_ticks
    lo, hi = np.floor(bars.low.to_numpy() / step).astype(np.int64), np.floor(bars.high.to_numpy() / step).astype(np.int64)
    base = lo.min()
    hist = np.zeros(hi.max() - base + 1)
    vol = bars.volume.to_numpy(dtype=float)
    for a, b, v in zip(lo - base, hi - base, vol):
        hist[a:b + 1] += v / (b - a + 1)
    poc = int(hist.argmax())
    lo_i = hi_i = poc
    total, acc = hist.sum(), hist[poc]
    while acc < 0.7 * total and (lo_i > 0 or hi_i < len(hist) - 1):
        up = hist[hi_i + 1] if hi_i < len(hist) - 1 else -1
        dn = hist[lo_i - 1] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1; acc += up
        else:
            lo_i -= 1; acc += dn
    price = lambda i: (base + i + 0.5) * step
    return price(poc), price(hi_i), price(lo_i)


def vwap_bands(bars):
    if bars.empty or bars.volume.sum() <= 0:
        return None
    tp = ((bars.high + bars.low + bars.close) / 3).to_numpy()
    v = bars.volume.to_numpy(dtype=float)
    vw = float((tp * v).sum() / v.sum())
    sd = float(np.sqrt(max(((tp - vw) ** 2 * v).sum() / v.sum(), 0.0)))
    return vw, sd


def levels_at(prior: pd.DataFrame, current: pd.DataFrame, history: pd.DataFrame, cutoff: int, tick: float, bin_ticks: int,
              ml: dict | None = None) -> dict:
    """Candidate levels known at `cutoff` (ET minutes) for the session in `current`.

    prior: annotated bars of the previous session; current: annotated bars of this session
    (bars after the cutoff are ignored here); history: daily rows (high, low, close) of
    sessions strictly before this one, oldest first.
    """
    cur = current[elapsed(current.minute.to_numpy(), cutoff)]
    out = {}
    if not prior.empty:
        h, l, c = float(prior.high.max()), float(prior.low.min()), float(prior.close.iloc[-1])
        out.update(PDH=h, PDL=l, PDC=c)
        vb = vwap_bands(prior)
        if vb:
            out["PD_VWAP"] = vb[0]
        prof = profile(prior, tick, bin_ticks)
        if prof:
            out.update(PD_POC=prof[0], PD_VAH=prof[1], PD_VAL=prof[2])
        rth = prior[_in(prior.minute, NY_OPEN, NY_CLOSE)]
        if not rth.empty:
            out.update(PRTH_H=float(rth.high.max()), PRTH_L=float(rth.low.min()))
        p = (h + l + c) / 3
        out.update(PIV_P=p, PIV_R1=2 * p - l, PIV_S1=2 * p - h, PIV_R2=p + (h - l), PIV_S2=p - (h - l))
    for key, start, end in (("ASIA", ASIA, LONDON), ("LON", LONDON, NY_OPEN)):
        seg = cur[_in(cur.minute, start, end)]
        if not seg.empty and _rel(cutoff) >= _rel(end):
            out[f"{key}_H"], out[f"{key}_L"] = float(seg.high.max()), float(seg.low.min())
    for key, minutes in (("ORB15", 15), ("ORB30", 30), ("IB", 60)):
        seg = cur[_in(cur.minute, NY_OPEN, NY_OPEN + minutes)]
        if not seg.empty and _rel(cutoff) >= _rel(NY_OPEN + minutes):
            out[f"{key}_H"], out[f"{key}_L"] = float(seg.high.max()), float(seg.low.min())
    vb = vwap_bands(cur)
    if vb:
        vw, sd = vb
        out.update(VWAP=vw, VWAP_U1=vw + sd, VWAP_L1=vw - sd, VWAP_U2=vw + 2 * sd, VWAP_L2=vw - 2 * sd)
    if len(history) >= 5:
        out.update(W5_H=float(history.high.tail(5).max()), W5_L=float(history.low.tail(5).min()))
    if len(history) >= 20:
        out.update(W20_H=float(history.high.tail(20).max()), W20_L=float(history.low.tail(20).min()),
                   EMA20D=float(history.close.ewm(span=20, adjust=False).mean().iloc[-1]))
    if len(history) >= 50:
        out["EMA50D"] = float(history.close.ewm(span=50, adjust=False).mean().iloc[-1])
    if len(history) >= 200:
        out["SMA200D"] = float(history.close.tail(200).mean())
    for key, value in (ml or {}).items():
        if value is not None and np.isfinite(value):
            out[key] = float(value)
    return out


def confluence(levels: dict, tolerance: float) -> dict:
    """For each level, the number of *other* levels (different source groups count once each) within tolerance."""
    keys = list(levels)
    prices = np.array([levels[k] for k in keys])
    out = {}
    for i, k in enumerate(keys):
        near = [keys[j] for j in np.flatnonzero(np.abs(prices - prices[i]) <= tolerance) if j != i]
        out[k] = {"count": len(near), "groups": len({GROUP[n] for n in near} - {GROUP[k]}), "with": near}
    return out


def session_state(current: pd.DataFrame, cutoff: int) -> dict:
    """Intraday state at the cutoff: price vs VWAP, opening-range breakout, IB position."""
    cur = current[elapsed(current.minute.to_numpy(), cutoff)]
    if cur.empty:
        return {}
    price = float(cur.close.iloc[-1])
    vb = vwap_bands(cur)
    state = {"price": price, "vs_vwap": None if not vb else (price - vb[0]) / vb[1] if vb[1] > 0 else 0.0}
    orb = cur[_in(cur.minute, NY_OPEN, NY_OPEN + 30)]
    if not orb.empty and _rel(cutoff) >= _rel(NY_OPEN + 30):
        hi, lo = orb.high.max(), orb.low.min()
        state["orb"] = "above" if price > hi else "below" if price < lo else "inside"
    return state
