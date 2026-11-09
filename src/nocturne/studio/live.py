"""Live (delayed) session view: today's Asia/London/NY levels, touch probabilities, state.

Bars come from Yahoo's free continuous futures chart (about 10 minutes delayed; not an
exchange feed). Probabilities come from the walk-forward level model trained on authentic
Databento contract bars, applied at the latest cutoff that has passed (03:00 / 09:30 /
10:30 ET). Levels traded after that cutoff are marked HIT with the time they printed.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..adapters import yahoo
from ..instruments import get_instrument
from . import STATE, indicators, levelmodel, market, predictor, sessions

SYMBOL = {"NQ": "NQ=F", "ES": "ES=F"}
TTL = 60
_cache: dict = {}
_lock = threading.Lock()


def _frame(payload):
    r = payload["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    f = pd.DataFrame({"timestamp": pd.to_datetime(r["timestamp"], unit="s", utc=True), "open": q["open"], "high": q["high"],
                      "low": q["low"], "close": q["close"], "volume": q["volume"]}).dropna(subset=["open", "high", "low", "close"])
    f["volume"] = f.volume.fillna(0).astype(float)
    return f.reset_index(drop=True), r.get("meta", {})


def fetch(root):
    """5m (60 days), 1m (today) and daily (2 years) bars; cached for TTL seconds."""
    with _lock:
        hit = _cache.get(root)
        if hit and time.time() - hit["at"] < TTL:
            return hit
    symbol = SYMBOL[root]
    five, meta = _frame(yahoo.fetch_chart(symbol, "60d", "5m", retries=2, pause=1.0))
    one, _ = _frame(yahoo.fetch_chart(symbol, "1d", "1m", retries=2, pause=1.0))
    daily, _ = _frame(yahoo.fetch_chart(symbol, "2y", "1d", retries=2, pause=1.0))
    entry = {"at": time.time(), "five": five, "one": one, "daily": daily, "meta": meta}
    with _lock:
        _cache[root] = entry
    return entry


def _history(daily_from_five, yahoo_daily, before_session):
    """Session high/low/close history strictly before `before_session` (5m-derived, older from Yahoo daily)."""
    h = daily_from_five[daily_from_five.index < before_session][["high", "low", "close"]]
    first = h.index.min() if len(h) else before_session
    yd = yahoo_daily.assign(d=yahoo_daily.timestamp.dt.tz_convert(sessions.ET).dt.date.astype(str))
    older = yd[yd.d < first].set_index("d")[["high", "low", "close"]]
    return pd.concat([older, h])


def _trend(history):
    close = history.close
    if len(close) < 60:
        return {"label": "Unknown"}
    e20, e50 = close.ewm(span=20, adjust=False).mean().iloc[-1], close.ewm(span=50, adjust=False).mean().iloc[-1]
    adx = float(indicators.adx(history.assign(open=history.close), 14).iloc[-1])
    c = float(close.iloc[-1])
    label = "Uptrend" if c > e20 > e50 and adx >= 20 else "Downtrend" if c < e20 < e50 and adx >= 20 else "Range"
    return {"label": label, "close": c, "ema20": round(float(e20), 2), "ema50": round(float(e50), 2), "adx": round(adx, 1)}


def trend_record(root):
    """How often each daily trend label was followed by a higher next-session settle (Databento, 2010-)."""
    path = levelmodel.DIR / f"{root}_{levelmodel._key(root)}_trend.json"
    if path.exists():
        return json.loads(path.read_text())
    five, _ = market.bars(root, "1d", limit=100000, source="databento")
    d = five.set_index(five.timestamp.dt.tz_convert(sessions.ET).dt.date.astype(str))[["high", "low", "close"]]
    e20, e50 = d.close.ewm(span=20, adjust=False).mean(), d.close.ewm(span=50, adjust=False).mean()
    adx = indicators.adx(d.assign(open=d.close), 14)
    label = np.where((d.close > e20) & (e20 > e50) & (adx >= 20), "Uptrend", np.where((d.close < e20) & (e20 < e50) & (adx >= 20), "Downtrend", "Range"))
    nxt = (d.close.shift(-1) > d.close).astype(float).where(d.close.shift(-1).notna())
    f = pd.DataFrame({"label": label, "up": nxt}).iloc[60:].dropna()
    out = {"all": {"n": int(len(f)), "p_next_up": round(float(f.up.mean()), 3)}}
    for k, g in f.groupby("label"):
        out[k] = {"n": int(len(g)), "p_next_up": round(float(g.up.mean()), 3)}
    levelmodel.DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def _cutoff_for(minute_now):
    rel = sessions._rel(minute_now)
    chosen = None
    for name, m in sessions.CUTOFFS.items():
        if rel >= sessions._rel(m):
            chosen = name
    return chosen


def snapshot(root):
    if root not in SYMBOL:
        raise ValueError("unsupported instrument")
    spec = get_instrument(root)
    data = fetch(root)
    bars = sessions.annotate(data["five"])
    one = sessions.annotate(data["one"]) if len(data["one"]) else bars
    daily5 = levelmodel.daily_from(bars.assign(instrument_id=0))
    days = list(daily5.index)
    now_et = pd.Timestamp.now(tz=sessions.ET)
    last_ts = pd.Timestamp(one.timestamp.iloc[-1])
    current_day = days[-1]
    current, prior = bars[bars.session == current_day], bars[bars.session == days[-2]]
    now_min = now_et.hour * 60 + now_et.minute
    closed = sessions.NY_CLOSE <= now_min < sessions.ASIA or now_et.weekday() == 5 or (now_et.weekday() == 6 and now_min < sessions.ASIA) \
        or (now_et.weekday() == 4 and now_min >= sessions.NY_CLOSE)
    history = _history(daily5, data["daily"], current_day)
    atr = float(levelmodel.atr20(history.assign(open=history.close)).iloc[-1])
    price = float(one.close.iloc[-1])
    cutoff = _cutoff_for(int(current.minute.iloc[-1]) if len(current) else now_min)
    ml = None
    try:
        pred = predictor.predict(root)
        if pred["target_session"] == current_day:
            ml = {"ML_UP50": pred["projected"]["high"]["p50"], "ML_UP25": pred["projected"]["high"]["p75"],
                  "ML_DN50": pred["projected"]["low"]["p50"], "ML_DN25": pred["projected"]["low"]["p75"]}
    except Exception:  # noqa: BLE001 - ML levels are optional context
        pred = None
    out = {"root": root, "symbol": SYMBOL[root], "session": current_day, "price": price, "last_bar": str(last_ts),
           "delay_minutes": round((pd.Timestamp.now(tz="UTC") - last_ts).total_seconds() / 60 - 1, 1),
           "atr20": round(atr, 2), "source": "Yahoo continuous futures (free, delayed ~10 min) · probabilities from authentic Databento model",
           "closed": bool(closed), "cutoff": cutoff, "cutoff_label": sessions.CUTOFF_LABEL.get(cutoff), "trading_decision": "NO_TRADE"}
    # Session map (always, from bars up to now)
    seg = {}
    for key, start, end in (("Asia", sessions.ASIA, sessions.LONDON), ("London", sessions.LONDON, sessions.NY_OPEN), ("New York", sessions.NY_OPEN, sessions.NY_CLOSE)):
        g = current[sessions._in(current.minute, start, end)]
        seg[key] = None if g.empty else {"open": float(g.open.iloc[0]), "high": float(g.high.max()), "low": float(g.low.min()),
                                         "last": float(g.close.iloc[-1]), "complete": bool(sessions._rel(int(current.minute.iloc[-1])) + 5 >= sessions._rel(end))}
    out["sessions"] = seg
    for key, minutes in (("orb15", 15), ("orb30", 30), ("ib", 60)):
        g = current[sessions._in(current.minute, sessions.NY_OPEN, sessions.NY_OPEN + minutes)]
        done = len(current) and sessions._rel(int(current.minute.iloc[-1])) + 5 >= sessions._rel(sessions.NY_OPEN + minutes)
        out[key] = None if g.empty or not done else {"high": float(g.high.max()), "low": float(g.low.min())}
    vb = sessions.vwap_bands(current)
    out["vwap"] = None if not vb else {"vwap": round(vb[0], 2), "sd": round(vb[1], 2), "u1": round(vb[0] + vb[1], 2), "l1": round(vb[0] - vb[1], 2),
                                         "u2": round(vb[0] + 2 * vb[1], 2), "l2": round(vb[0] - 2 * vb[1], 2),
                                         "position_sd": round((price - vb[0]) / vb[1], 2) if vb[1] > 0 else 0.0}
    # Level probabilities at the latest passed cutoff
    levels = []
    if cutoff and not prior.empty:
        rows, _ = levelmodel.rows_for_session(root, prior, current, history, atr, ml, cutoff)
        if rows:
            frame = pd.DataFrame(rows)
            frame["p"] = levelmodel.score(root, frame)
            cut_rel = sessions._rel(sessions.CUTOFFS[cutoff])
            after = one[(one.session == current_day) & (sessions._rel(one.minute.to_numpy()) >= cut_rel)]
            conf = sessions.confluence({r["key"]: r["price"] for r in rows}, 0.1 * atr)
            for r in frame.to_dict("records"):
                hit_time = None
                if not after.empty:
                    m = (after.low <= r["price"]) & (after.high >= r["price"])
                    if m.any():
                        hit_time = str(pd.Timestamp(after.timestamp[m].iloc[0]).tz_convert(sessions.ET).strftime("%H:%M"))
                levels.append({"key": r["key"], "name": sessions.LEVEL_NAMES[r["key"]], "group": sessions.GROUP[r["key"]],
                               "price": round(r["price"], 2), "distance": round(r["price"] - price, 2),
                               "probability": round(float(r["p"]), 3), "status": "HIT" if hit_time else "OPEN", "hit_at": hit_time,
                               "confluence": [sessions.LEVEL_NAMES[k] for k in conf[r["key"]]["with"]]})
    levels.sort(key=lambda x: -x["price"])
    out["levels"] = levels
    open_lv = [l for l in levels if l["status"] == "OPEN"]
    pick = lambda side: sorted([l for l in open_lv if (l["distance"] > 0) == (side == "up") and abs(l["distance"]) >= 0.1 * atr],
                               key=lambda l: abs(l["distance"]))
    out["targets"] = {side: [{**l, "tp": f"TP{i + 1}"} for i, l in enumerate([x for x in pick(side) if x["probability"] >= 0.25][:3])] for side in ("up", "down")}
    # Market state with measured follow-through
    trend = _trend(history)
    tr = trend_record(root)
    study = levelmodel.study(root)
    intraday = {}
    if cutoff:
        d = study["direction_rest_of_day"].get(sessions.CUTOFF_LABEL[cutoff], {})
        pos = out["vwap"]["position_sd"] if out["vwap"] else 0
        key = "above VWAP +1σ" if pos > 1 else "above VWAP" if pos > 0 else "below VWAP −1σ" if pos < -1 else "below VWAP"
        intraday = {"vwap_state": key, "measured": d.get(key), "baseline": d.get("close_above_cutoff_price")}
        if out["orb30"]:
            o = "above" if price > out["orb30"]["high"] else "below" if price < out["orb30"]["low"] else "inside"
            intraday.update(orb_state=o, orb_measured=d.get(f"ORB {o}"))
    regime = pred["regime"] if pred and pred.get("target_session") == current_day else None
    bias = _bias(trend, intraday, regime)
    out["state"] = {"daily": {**trend, "measured": tr.get(trend["label"]), "baseline": tr.get("all")}, "intraday": intraday, "regime": regime, **bias}
    out["model"] = {k: study[k] for k in ("auc", "auc_distance_only", "auc_without_confluence", "calibration", "useful_targets", "by_confluence_groups")}
    recent = data["five"][data["five"].timestamp >= data["five"].timestamp.iloc[-1] - pd.Timedelta(days=4)]
    out["bars"] = [{"t": int(r.timestamp.timestamp()), "o": r.open, "h": r.high, "l": r.low, "c": r.close, "v": r.volume}
                   for r in recent.itertuples(index=False)]
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    return market.json_safe(out)


def _bias(trend, intraday, regime):
    """Plain-language state; every claim carries its measured follow-through rate."""
    t = trend.get("label", "Unknown")
    m = (intraday or {}).get("measured") or {}
    base = (intraday or {}).get("baseline")
    p = m.get("p_close_higher")
    if regime and regime["compression"]["probability"] > regime["compression"]["base_rate"] * 1.3:
        headline = "Consolidation likely"
    elif t == "Uptrend" and (p is None or p >= 0.55):
        headline = "Bullish"
    elif t == "Downtrend" and (p is None or p <= 0.53):
        headline = "Bearish"
    elif p is not None and base is not None and p - base >= 0.02:
        headline = "Leaning bullish"
    elif p is not None and base is not None and base - p >= 0.02:
        headline = "Leaning bearish"
    else:
        headline = "Neutral / two-way"
    edge = None if p is None or base is None else round(p - base, 3)
    return {"headline": headline, "edge_vs_baseline": edge,
            "confidence": "weak" if edge is None or abs(edge) < 0.05 else "moderate" if abs(edge) < 0.1 else "strong"}


def quote(root):
    """Lightweight delayed quote for the header ticker (shares the fetch cache)."""
    data = fetch(root)
    bars = sessions.annotate(data["five"])
    closes = bars.groupby("session", sort=True).close.last()
    one = data["one"] if len(data["one"]) else data["five"]
    price = float(one.close.iloc[-1])
    prior = float(closes.iloc[-2]) if len(closes) > 1 else None
    return {"root": root, "price": price, "prior_settle": prior, "change": None if prior is None else round(price - prior, 2),
            "change_pct": None if not prior else round((price / prior - 1) * 100, 2), "last_bar": str(one.timestamp.iloc[-1]),
            "delayed": True}
