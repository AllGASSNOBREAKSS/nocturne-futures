"""Session-level research dataset from authentic Databento NQ/ES contract bars.

One row per Globex session D (18:00 ET D-1 -> 17:00 ET D). Features are known
at 17:59 ET on D (before session D+1 opens); every label describes session D+1.
Returns are computed within one contract only (a roll never becomes a return),
and labels whose next session is on a different contract are dropped. Baselines
are trailing frequencies of labels that had already been realised at the cutoff.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from ..research.free_data_experiment import free_features
from . import market
from .indicators import globex_session

TBS_GEOMETRIES = {"0.25x0.25": (0.25, 0.25), "0.5x0.25": (0.5, 0.25), "0.5x0.5": (0.5, 0.5), "1.0x0.5": (1.0, 0.5)}
POINT_THRESHOLDS = {"NQ": (100, 200, 350, 500), "ES": (25, 50, 100, 150)}
ATR_THRESHOLDS = (0.75, 1.0, 1.5, 2.0)
INTRADAY = ["on_range_atr", "rth_range_atr", "ib_range_atr", "close_location", "rth_return", "last_hour_return",
            "vwap_distance_atr", "volume_z"]
PRICE = ["ret_1", "ret_5", "ret_20", "vol_20", "range_pts", "atr20_pts", "range_atr", "log_level", "pos_20"]
COST_POINTS = 0.75


def _intraday(root, source="databento"):
    five, _ = market.bars(root, "5m", limit=50_000_000, source=source)
    if "instrument_id" not in five:
        five["instrument_id"] = 0  # continuous proxy: contract identity unknown
    five["session"] = globex_session(five.timestamp)
    et = five.timestamp.dt.tz_convert("America/New_York")
    minute = et.dt.hour * 60 + et.dt.minute
    five["rth"] = (minute >= 570) & (minute < 960)
    five["ib"] = (minute >= 570) & (minute < 630)
    five["on"] = ~five.rth & (minute < 570) | (minute >= 1080)
    five["last_hour"] = (minute >= 900) & (minute < 960)
    five["minute"] = minute
    five["typical_volume"] = (five.high + five.low + five.close) / 3 * five.volume
    g = five.groupby("session")
    out = pd.DataFrame({
        "on_high": five[five.on].groupby("session").high.max(), "on_low": five[five.on].groupby("session").low.min(),
        "rth_open": five[five.rth].groupby("session").open.first(), "rth_close": five[five.rth].groupby("session").close.last(),
        "rth_high": five[five.rth].groupby("session").high.max(), "rth_low": five[five.rth].groupby("session").low.min(),
        "ib_high": five[five.ib].groupby("session").high.max(), "ib_low": five[five.ib].groupby("session").low.min(),
        "lh_open": five[five.last_hour].groupby("session").open.first(), "lh_close": five[five.last_hour].groupby("session").close.last(),
        "vwap": g.typical_volume.sum() / g.volume.sum(), "contract_id": g.instrument_id.last(),
    })
    out.index = pd.Index(out.index, name="session")
    return out, five


def _tbs(five, rows):
    """Target-before-stop labels for session D+1 entered at its 10:00 ET 5m open.
    Distances are ATR20 multiples known at D's close; same-bar ties are stop-first."""
    by_session = {s: g for s, g in five[five.rth].groupby("session")}
    labels = {f"tbs_{side}_{k}": np.full(len(rows), np.nan) for k in TBS_GEOMETRIES for side in ("long", "short")}
    rs = {f"r_{side}_{k}": np.full(len(rows), np.nan) for k in TBS_GEOMETRIES for side in ("long", "short")}
    for i, (nxt, atr, contract) in enumerate(zip(rows.next_session, rows.atr20_pts, rows.contract_id)):
        g = by_session.get(nxt)
        if g is None or not np.isfinite(atr):
            continue
        g = g[g.minute >= 600]
        if g.empty or g.minute.iloc[0] != 600 or (g.instrument_id != contract).any():
            continue
        entry, hi, lo, last = g.open.iloc[0], g.high.to_numpy(), g.low.to_numpy(), g.close.iloc[-1]
        for key, (a, b) in TBS_GEOMETRIES.items():
            for side, sign in (("long", 1), ("short", -1)):
                tp, sl = entry + sign * a * atr, entry - sign * b * atr
                hit_t = (hi >= tp) if sign > 0 else (lo <= tp)
                hit_s = (lo <= sl) if sign > 0 else (hi >= sl)
                it = np.argmax(hit_t) if hit_t.any() else 10**9
                is_ = np.argmax(hit_s) if hit_s.any() else 10**9
                if it < is_:
                    label, r = 1.0, a / b
                elif is_ < 10**9:
                    label, r = 0.0, -1.0
                else:
                    label, r = 0.0, sign * (last - entry) / (b * atr)
                labels[f"tbs_{side}_{key}"][i] = label
                rs[f"r_{side}_{key}"][i] = r - COST_POINTS / (b * atr)
    return pd.DataFrame({**labels, **rs}, index=rows.index)


@lru_cache(maxsize=8)
def build(root, source="databento"):
    daily, meta = market.bars(root, "1d", limit=100000, source=source)
    if "instrument_id" not in daily:
        daily["instrument_id"] = 0
    daily = daily.assign(session=pd.to_datetime(daily.timestamp).dt.tz_convert("America/New_York").dt.date).set_index("session")
    intraday, five = _intraday(root, source)
    d = daily.join(intraday, how="inner")
    same = d.instrument_id.eq(d.instrument_id.shift())
    c, h, l = d.close, d.high, d.low
    rng = h - l
    daily_ret = (c / c.shift() - 1).where(same)
    clean = daily_ret.fillna(0.0)
    f = pd.DataFrame(index=d.index)
    f["ret_1"], f["ret_5"], f["ret_20"] = daily_ret, clean.rolling(5).sum(), clean.rolling(20).sum()
    f["vol_20"] = daily_ret.rolling(20, min_periods=15).std()
    f["range_pts"], f["atr20_pts"] = rng, rng.rolling(20).mean()
    f["range_atr"], f["log_level"] = rng / f.atr20_pts, np.log(c)
    f["pos_20"] = (c - l.rolling(20).min()) / (h.rolling(20).max() - l.rolling(20).min())
    atr = f.atr20_pts
    f["on_range_atr"] = (d.on_high - d.on_low) / atr
    f["rth_range_atr"] = (d.rth_high - d.rth_low) / atr
    f["ib_range_atr"] = (d.ib_high - d.ib_low) / atr
    f["close_location"] = (c - l) / rng.replace(0, np.nan)
    f["rth_return"] = d.rth_close / d.rth_open - 1
    f["last_hour_return"] = d.lh_close / d.lh_open - 1
    f["vwap_distance_atr"] = (c - d.vwap) / atr
    f["volume_z"] = (d.volume - d.volume.rolling(20).mean()) / d.volume.rolling(20).std()
    f["close"], f["contract_id"], f["year"] = c, d.instrument_id, pd.to_datetime(pd.Series(d.index, index=d.index)).dt.year
    f["prior_high"], f["prior_low"], f["prior_vwap"] = h, l, d.vwap
    # Session-D reference levels (known at the cutoff) for the next-session level map.
    for col in ("on_high", "on_low", "rth_high", "rth_low", "ib_high", "ib_low", "rth_open", "rth_close"):
        f[f"lvl_{col}"] = d[col]
    # next-session labels (dropped when the next session is on another contract)
    nxt_same = d.instrument_id.shift(-1).eq(d.instrument_id)
    nh, nl, nc, no = h.shift(-1), l.shift(-1), c.shift(-1), d.open.shift(-1)
    nrange = (nh - nl).where(nxt_same)
    f["next_session"] = pd.Series(d.index, index=d.index).shift(-1)
    # Directionless excursions of the next session from today's settle, in ATR units.
    f["up_exc_atr"] = ((nh - c) / atr).where(nxt_same)
    f["dn_exc_atr"] = ((c - nl) / atr).where(nxt_same)
    f["next_range"] = nrange
    labels = {"direction": (nc > c).astype(float), "compression": (nrange < 0.6 * atr).astype(float),
              "expansion": (nrange > 1.5 * atr).astype(float),
              "trend_day": (((nc - no).abs() > 0.6 * (nh - nl)) & (nrange > atr)).astype(float),
              "touch_prior_high": (nh >= h).astype(float), "touch_prior_low": (nl <= l).astype(float),
              "touch_prior_vwap": ((nh >= d.vwap) & (nl <= d.vwap)).astype(float)}
    labels |= {f"range_ge_{n}pts": (nrange >= n).astype(float) for n in POINT_THRESHOLDS[root]}
    labels |= {f"range_ge_{k}atr": (nrange >= k * atr).astype(float) for k in ATR_THRESHOLDS}
    for name, y in labels.items():
        y = y.where(nxt_same & nrange.notna())
        f[f"y_{name}"] = y
        # At cutoff D, the newest realised label is the one about session D (row D-1).
        f[f"base_{name}"] = y.shift(1).rolling(250, min_periods=120).mean()
    tbs = _tbs(five, f.assign(contract_id=d.instrument_id))
    for col in tbs:
        f[col] = tbs[col]
        if col.startswith("tbs_"):
            f[f"base_{col}"] = tbs[col].shift(1).rolling(250, min_periods=120).mean()
    cutoff = (pd.to_datetime(pd.Series(f.index, index=f.index).astype(str)).dt.tz_localize("America/New_York")
              + pd.Timedelta(hours=17, minutes=59)).dt.tz_convert("UTC")
    free, audit = free_features(market.archive(), cutoff.reset_index(drop=True))
    free.index = f.index
    f = pd.concat([f, free], axis=1).copy()  # one contiguous block (avoids fragmentation)
    f.index.name = "date"
    f = f.reset_index()
    f["date"] = f.date.astype(str)
    return f, {"source": meta["dataset"], "sessions": int(len(f)), "pit_audit": audit,
               "label_rule": "next Globex session; dropped when next session is a different contract",
               "baseline_rule": "trailing 250 realised labels (shifted by one session)"}


OBJECTIVES = {
    "direction": "Next settle above today's settle (same contract)",
    "compression": "Next session range < 0.6 x ATR20", "expansion": "Next session range > 1.5 x ATR20",
    "trend_day": "Next session |close-open| > 60% of range and range > ATR20",
    "touch_prior_high": "Next session trades at/above today's high", "touch_prior_low": "Next session trades at/below today's low",
    "touch_prior_vwap": "Next session trades through today's session VWAP",
}
