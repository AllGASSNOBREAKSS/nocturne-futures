"""World news, economic calendar and measured event impact.

- Headlines: public RSS feeds (CNBC, MarketWatch, Federal Reserve, BBC World, Google News),
  categorised by keyword with a small finance tone lexicon. Tone is descriptive only; it
  was not validated as predictive. For headlines published today we report the actual
  NQ/ES move since publication from delayed 1-minute bars.
- Calendar: ForexFactory's public weekly calendar (this week only).
- Impact: measured on authentic Databento sessions since 2010 for FOMC decision days
  (official Fed calendar pages) and 08:30 ET data days (detected from the 08:30 volume
  surge; first-Friday surges are labelled payrolls).
"""
from __future__ import annotations

import json
import re
import threading
import time
import xml.etree.ElementTree as ET_XML
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd
import requests

from . import STATE, market, sessions

DIR = STATE / "news"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FEEDS = {
    "CNBC Markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC Economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Google News: markets": "https://news.google.com/rss/search?q=stock+market+OR+nasdaq+OR+%22federal+reserve%22+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Google News: world": "https://news.google.com/rss/search?q=war+OR+tariffs+OR+sanctions+OR+oil+when:1d&hl=en-US&gl=US&ceid=US:en",
}
CALENDAR = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CATEGORIES = {
    "Fed & rates": r"\bfed\b|federal reserve|fomc|powell|rate (cut|hike)|interest rate|treasur|yield|central bank|ecb|boj|bank of england",
    "Inflation": r"inflation|\bcpi\b|\bppi\b|\bpce\b|prices rose|price index",
    "Jobs": r"payroll|jobs report|unemployment|jobless|labor market|hiring|layoff",
    "Growth": r"\bgdp\b|recession|retail sales|ism|manufacturing|consumer (spending|confidence)|economy",
    "Earnings & tech": r"earnings|revenue|guidance|nvidia|apple|microsoft|amazon|alphabet|google|meta|tesla|\bai\b|chip|semiconductor",
    "Trade & tariffs": r"tariff|trade (war|deal)|export (ban|control)|import",
    "Geopolitics": r"\bwar\b|missile|attack|military|invasion|sanction|ukraine|russia|israel|iran|taiwan|north korea|conflict|ceasefire",
    "Energy": r"\boil\b|opec|crude|natural gas|energy",
    "China": r"china|beijing|yuan|xi jinping",
    "Credit & banks": r"bank (run|failure)|default|credit|bond market|downgrade",
}
POSITIVE = r"rall(y|ies)|surge|soar|jump|gain|record high|beat|upgrade|cools|eases|rate cut|ceasefire|deal reached|optimis|rebound|strong"
NEGATIVE = r"plunge|slump|tumble|sell-?off|drop|fall|miss|downgrade|hot(ter)? inflation|rate hike|war|attack|sanction|tariff|default|recession|layoff|fear|crash|weak|escalat"
_cache: dict = {}
_lock = threading.Lock()


def _get(url, timeout=12):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def headlines():
    with _lock:
        hit = _cache.get("headlines")
        if hit and time.time() - hit[0] < 300:
            return hit[1]
    items, errors = [], {}
    for source, url in FEEDS.items():
        try:
            root = ET_XML.fromstring(_get(url).content)
        except Exception as exc:  # noqa: BLE001 - one bad feed must not hide the rest
            errors[source] = type(exc).__name__
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            pub = it.findtext("pubDate")
            try:
                when = parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None
            except (TypeError, ValueError):
                when = None
            if not title or when is None:
                continue
            text = title.lower()
            cats = [k for k, rx in CATEGORIES.items() if re.search(rx, text)]
            pos, neg = len(re.findall(POSITIVE, text)), len(re.findall(NEGATIVE, text))
            items.append({"title": title, "link": it.findtext("link"), "source": source, "published_at": when.isoformat(),
                          "categories": cats or ["Other"], "tone": "positive" if pos > neg else "negative" if neg > pos else "neutral"})
    seen, unique = set(), []
    for x in sorted(items, key=lambda x: x["published_at"], reverse=True):
        key = re.sub(r"\W+", " ", x["title"].lower())[:80]
        if key not in seen:
            seen.add(key)
            unique.append(x)
    result = {"items": unique[:120], "errors": errors, "fetched_at": datetime.now(timezone.utc).isoformat()}
    with _lock:
        _cache["headlines"] = (time.time(), result)
    return result


EVENT_TYPE = [("Fed speaker", r"speaks|testif"), ("FOMC", r"federal funds rate|fomc statement|fomc press|fomc economic projections"), ("CPI", r"\bcpi\b"), ("Payrolls", r"non-farm|nonfarm"),
              ("PPI", r"\bppi\b"), ("PCE", r"\bpce\b"), ("Retail sales", r"retail sales"), ("GDP", r"\bgdp\b"),
              ("Jobless claims", r"unemployment claims|jobless"), ("ISM", r"\bism\b"), ("JOLTS", r"jolts")]


def calendar():
    with _lock:
        hit = _cache.get("calendar")
        if hit and time.time() - hit[0] < 1800:
            return hit[1]
    try:
        raw = _get(CALENDAR).json()
    except Exception as exc:  # noqa: BLE001
        return {"events": [], "error": type(exc).__name__}
    out = []
    for e in raw:
        if e.get("impact") not in ("High", "Medium") or e.get("country") not in ("USD", "EUR", "GBP", "JPY", "CNY"):
            continue
        kind = next((k for k, rx in EVENT_TYPE if re.search(rx, e["title"].lower())), None) if e["country"] == "USD" else None
        out.append({"title": e["title"], "country": e["country"], "time": e["date"], "impact": e["impact"], "forecast": e.get("forecast"),
                    "previous": e.get("previous"), "type": kind})
    result = {"events": sorted(out, key=lambda x: x["time"]), "source": "ForexFactory weekly calendar (public)"}
    with _lock:
        _cache["calendar"] = (time.time(), result)
    return result


def fomc_dates():
    """FOMC decision dates (last day of each scheduled meeting) from federalreserve.gov."""
    path = DIR / "fomc_dates.json"
    if path.exists():
        return json.loads(path.read_text())
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    dates = set()
    pages = [f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm" for y in range(2010, 2021)]
    pages.append("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    for url in pages:
        try:
            html = _get(url, timeout=30).text
        except Exception:  # noqa: BLE001
            continue
        if "fomchistorical" in url:
            year = int(url[-8:-4])
            for m, a, b in re.findall(rf"({months})\s+(\d{{1,2}})(?:-(\d{{1,2}}))?\s+(?:FOMC\s+)?Meeting", html):
                dates.add(str(pd.Timestamp(f"{m} {b or a} {year}").date()))
        else:
            for block in re.split(r'<h4><a id="\d+">', html)[1:]:
                year = int(re.match(r"(\d{4})", block).group(1))
                for m, a, b in re.findall(rf'fomc-meeting__month[^>]*><strong>({months})(?:/\w+)?</strong>.*?fomc-meeting__date[^>]*>(\d{{1,2}})(?:-(\d{{1,2}}))?', block, re.S):
                    dates.add(str(pd.Timestamp(f"{m} {b or a} {year}").date()))
    out = sorted(d for d in dates if "2010-01-01" <= d)
    DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def event_study(root):
    """Measured reaction on FOMC and 08:30 data days vs all other sessions (Databento 5m)."""
    path = DIR / f"{root}_events.json"
    manifest = json.loads((market.DATABENTO / "manifest.json").read_text())
    key = manifest[root + "_5m"]["sha256"][:16]
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("key") == key:
            return cached
    five, _ = market.bars(root, "5m", limit=50_000_000, source="databento")
    bars = sessions.annotate(five)
    g = bars.groupby("session", sort=True)
    daily = pd.DataFrame({"high": g.high.max(), "low": g.low.min(), "close": g.close.last()})
    prev = daily.close.shift(1)
    tr = np.maximum(daily.high - daily.low, np.maximum((daily.high - prev).abs(), (daily.low - prev).abs()))
    atr = tr.rolling(20).mean().shift(1)
    def at(minute):
        x = bars[bars.minute == minute].groupby("session").first()
        return x
    b0800 = bars[(bars.minute >= 8 * 60) & (bars.minute < 8 * 60 + 30)].groupby("session").volume.median()
    b0830 = at(8 * 60 + 30)
    c0925 = bars[bars.minute == 9 * 60 + 25].groupby("session").close.first()
    o0830 = b0830.open
    surge = (b0830.volume / b0800).reindex(daily.index)
    rth = bars[(bars.minute >= sessions.NY_OPEN) & (bars.minute < sessions.NY_CLOSE)].groupby("session")
    rng = ((rth.high.max() - rth.low.min()) / atr).reindex(daily.index)
    rth_up = (rth.close.last() > rth.open.first()).reindex(daily.index)
    fomc = set(fomc_dates())
    o1400 = bars[bars.minute == 14 * 60].groupby("session").open.first()
    c1455 = bars[bars.minute == 14 * 60 + 55].groupby("session").close.first()
    frame = pd.DataFrame({"range_atr": rng, "up": rth_up, "surge": surge, "m830": ((c0925 - o0830).abs() / atr).reindex(daily.index),
                          "m1400": ((c1455 - o1400).abs() / atr).reindex(daily.index)}).dropna(subset=["range_atr"])
    idx = pd.to_datetime(frame.index)
    frame["fomc"] = frame.index.isin(fomc)
    frame["data830"] = frame.surge >= 4
    frame["payrolls"] = frame.data830 & (idx.weekday == 4) & (idx.day <= 10)
    normal = frame[~frame.fomc & ~frame.data830]
    def stats(g, window):
        return {"sessions": int(len(g)), "ny_range_vs_normal": round(float(g.range_atr.mean() / normal.range_atr.mean()), 2),
                "big_day_rate": round(float((g.range_atr > 1.5).mean()), 3), "normal_big_day_rate": round(float((normal.range_atr > 1.5).mean()), 3),
                "p_ny_close_up": round(float(g.up.mean()), 3), "normal_p_ny_close_up": round(float(normal.up.mean()), 3),
                "first_hour_move_atr": round(float(g[window].mean()), 3), "normal_first_hour_move_atr": round(float(normal[window].mean()), 3)}
    out = {"key": key, "root": root, "FOMC": stats(frame[frame.fomc], "m1400"), "Payrolls": stats(frame[frame.payrolls], "m830"),
           "08:30 data (CPI/PPI/retail/GDP…)": stats(frame[frame.data830 & ~frame.payrolls], "m830"),
           "method": "FOMC: official Fed calendar decision days, 14:00-15:00 ET move. 08:30 data days: 08:30 5m volume >= 4x the 08:00-08:30 median; "
                     "payrolls = such Fridays in days 1-10. Moves in ATR(20) units; NY = 09:30-16:00 ET."}
    DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    return out


def impact_for(kind, studies):
    if kind == "FOMC":
        return studies.get("FOMC")
    if kind == "Payrolls":
        return studies.get("Payrolls")
    if kind in ("CPI", "PPI", "PCE", "Retail sales", "GDP", "Jobless claims", "JOLTS", "ISM"):
        return studies.get("08:30 data (CPI/PPI/retail/GDP…)")
    return None


def brief(root, live_one=None):
    """Headlines + calendar + measured impact for the app."""
    h, cal = headlines(), calendar()
    study = event_study(root)
    for e in cal["events"]:
        e["measured_impact"] = impact_for(e["type"], study)
    if live_one is not None and len(live_one):
        ts = pd.DatetimeIndex(live_one.timestamp)
        last = float(live_one.close.iloc[-1])
        for item in h["items"]:
            t = pd.Timestamp(item["published_at"])
            i = ts.searchsorted(t)
            if 0 < i < len(ts):
                item["move_since"] = round(last - float(live_one.close.iloc[i - 1]), 2)
    counts = pd.Series([c for x in h["items"][:60] for c in x["categories"]]).value_counts().head(6).to_dict() if h["items"] else {}
    tone = pd.Series([x["tone"] for x in h["items"][:60]]).value_counts().to_dict() if h["items"] else {}
    return {"headlines": h["items"][:60], "feed_errors": h["errors"], "calendar": cal, "event_study": study,
            "themes": counts, "tone": tone,
            "note": "Headline tone is descriptive and was not validated as predictive. Scheduled-event impact is measured on 2010-2026 contract bars."}
