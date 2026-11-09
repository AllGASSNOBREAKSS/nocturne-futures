"""Free source definitions with explicit credibility and point-in-time rules.

Each normalized row carries ``available_at`` (UTC): the earliest time the value
could have been known by a market participant, chosen conservatively. Rows with
``pit_eligible = False`` are context only and must never enter a historical
backtest, because the provider serves revised/retrospective values without
publication vintages.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
from pandas.tseries.offsets import BDay

from ..adapters import bls as bls_adapter
from ..adapters import fred as fred_adapter

UTC = timezone.utc

# Credibility vocabulary (ordered): official statistical agency / regulator,
# official market-data distributor, unofficial research-grade, aggregated media.
OFFICIAL, OFFICIAL_DISTRIBUTOR, UNOFFICIAL, AGGREGATOR = (
    "OFFICIAL_PRIMARY", "OFFICIAL_DISTRIBUTOR", "UNOFFICIAL_RESEARCH_GRADE", "MEDIA_AGGREGATOR_UNVERIFIED")

# FRED: (business-day publication lag, pit_eligible, rationale)
FRED_RULES = {
    "VIXCLS": (0, True, "CBOE close known after the session"),
    "VXNCLS": (0, True, "CBOE close known after the session"),
    "RRPONTSYD": (0, True, "NY Fed publishes the same afternoon"),
    "DGS10": (1, True, "H.15 posted next business day ~16:15 ET"),
    "DGS2": (1, True, "H.15 posted next business day ~16:15 ET"),
    "DFF": (1, True, "EFFR published next business day"),
    "T10Y2Y": (1, True, "derived from next-day H.15"),
    "T10YIE": (1, True, "derived from next-day H.15"),
    "BAA10Y": (1, True, "Moody's/H.15 next business day"),
    "WALCL": (2, True, "H.4.1 Thursday 16:30 ET for Wednesday level; +1 day margin"),
    "DTWEXBGS": (7, True, "H.10 released weekly for the prior week"),
    "NASDAQ100": (1, False, "reference close for reconciliation, not a feature"),
    "NFCI": (7, False, "weekly index revised retrospectively; no vintage here"),
    "CPIAUCSL": (45, False, "monthly, seasonally revised; ALFRED vintages required"),
    "UNRATE": (35, False, "monthly, seasonally revised; ALFRED vintages required"),
    "USREC": (365, False, "NBER dates assigned months/years later"),
}

# CFTC Traders in Financial Futures, futures-only (official public reporting API).
CFTC_DATASET = "gpe5-46if"
CFTC_MARKETS = {"209742": "E-mini Nasdaq-100", "13874A": "E-mini S&P 500",
                "043602": "10-year T-note", "042601": "2-year T-note"}
CFTC_FIELDS = ("report_date_as_yyyy_mm_dd", "cftc_contract_market_code", "market_and_exchange_names",
               "open_interest_all", "asset_mgr_positions_long", "asset_mgr_positions_short",
               "lev_money_positions_long", "lev_money_positions_short",
               "dealer_positions_long_all", "dealer_positions_short_all",
               "change_in_open_interest_all")
# Tuesday positions are normally released Friday 15:30 ET. Use the following
# Monday 21:00 UTC to absorb holiday slips. Government shutdowns delayed releases
# for weeks; these windows use deliberately late, conservative availability.
COT_SHUTDOWNS = (("2013-10-01", "2013-11-12", "2013-11-30"),
                 ("2018-12-25", "2019-02-26", "2019-03-09"),
                 ("2025-09-30", "2025-12-30", "2026-01-31"))

SEC_TICKERS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "COST", "NFLX")
SEC_FORMS = {"10-K", "10-Q", "8-K"}

FED_EVENT_RULES = (("FOMC_STATEMENT", r"FOMC statement|Federal Open Market Committee (issues|statement)"),
                   ("FOMC_MINUTES", r"[Mm]inutes of the Federal Open Market Committee"),
                   ("MONETARY_POLICY", r"[Mm]onetary policy|discount rate|interest on reserve"),
                   ("BANK_SUPERVISION", r"[Ee]nforcement|[Ss]upervis|stress test|capital"),
                   ("TESTIMONY_SPEECH", r"[Tt]estimony|[Ss]peech"))

GDELT_QUERIES = {"fed_policy": '"Federal Reserve" (rate OR inflation)',
                 "us_inflation": '"consumer price index" OR "inflation report"',
                 "nasdaq_market": '"Nasdaq" (selloff OR rally OR futures)'}


def _after_bdays(dates, lag, hour_utc=22):
    dates = pd.to_datetime(dates)
    return (dates + BDay(lag)).dt.normalize().dt.tz_localize("UTC") + pd.Timedelta(hours=hour_utc) \
        if lag else dates.dt.normalize().dt.tz_localize("UTC") + pd.Timedelta(hours=hour_utc)


def cot_available_at(report_dates):
    dates = pd.to_datetime(report_dates)
    available = dates.dt.normalize().dt.tz_localize("UTC") + pd.Timedelta(days=6, hours=21)
    for start, end, released in COT_SHUTDOWNS:
        mask = (dates >= start) & (dates <= end)
        late = pd.Timestamp(released, tz="UTC") + pd.Timedelta(hours=21)
        available = available.where(~mask, late)
    return available


def collect_fred(client, archive, series=None, start="1986-01-01"):
    entries = []
    end = datetime.now(UTC).date().isoformat()
    for name in series or FRED_RULES:
        lag, eligible, why = FRED_RULES[name]
        response = client.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                              params={"id": name, "cosd": start, "coed": end})
        frame = fred_adapter.parse_series(response.content, name).dropna(subset=["value"])
        frame = frame.assign(date=frame.date.dt.date.astype(str),
                             available_at=_after_bdays(frame.date, lag).astype(str),
                             pit_eligible=eligible)
        entries.append(archive.record("fred", name, response.content, frame, ["date"],
                                      {"url": response.url, "credibility": OFFICIAL_DISTRIBUTOR,
                                       "availability_rule": f"+{lag} business days 22:00 UTC: {why}",
                                       "pit_eligible": eligible, "first": frame.date.min(), "last": frame.date.max()},
                                      ["value"]))
    return entries


def collect_cftc(client, archive, start="2006-01-01"):
    rows, raw_pages, offset = [], [], 0
    codes = ",".join(f"'{c}'" for c in CFTC_MARKETS)
    while True:
        response = client.get(f"https://publicreporting.cftc.gov/resource/{CFTC_DATASET}.json",
                              params={"$select": ",".join(CFTC_FIELDS),
                                      "$where": f"cftc_contract_market_code in ({codes}) AND report_date_as_yyyy_mm_dd >= '{start}'",
                                      "$order": "report_date_as_yyyy_mm_dd,cftc_contract_market_code",
                                      "$limit": 5000, "$offset": offset})
        page = json.loads(response.content)
        raw_pages.append(response.content)
        rows.extend(page)
        if len(page) < 5000:
            break
        offset += len(page)
        if offset > 100000:
            raise ValueError("CFTC pagination budget exceeded")
    frame = pd.DataFrame(rows)
    frame["report_date"] = pd.to_datetime(frame.pop("report_date_as_yyyy_mm_dd")).dt.date.astype(str)
    numeric = [c for c in CFTC_FIELDS if c not in ("report_date_as_yyyy_mm_dd", "cftc_contract_market_code", "market_and_exchange_names")]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame["market"] = frame.cftc_contract_market_code.map(CFTC_MARKETS)
    frame["available_at"] = cot_available_at(frame.report_date).astype(str)
    frame["pit_eligible"] = True
    raw = b"[" + b",".join(raw_pages) + b"]"
    return [archive.record("cftc", "tff_futures_only", raw, frame, ["report_date", "cftc_contract_market_code"],
                           {"url": f"https://publicreporting.cftc.gov/resource/{CFTC_DATASET}.json",
                            "credibility": OFFICIAL, "pages": len(raw_pages),
                            "availability_rule": "report Tuesday + 6 days 21:00 UTC; shutdown backlogs use conservative late dates",
                            "pit_eligible": True, "first": frame.report_date.min(), "last": frame.report_date.max()},
                           numeric)]


def collect_treasury(client, archive, start="2005-10-01"):
    rows, raw_pages, page = [], [], 1
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
    while True:
        response = client.get(url, params={"filter": f"record_date:gte:{start}", "sort": "record_date",
                                           "page[size]": 10000, "page[number]": page})
        payload = json.loads(response.content)
        raw_pages.append(response.content)
        rows.extend(payload["data"])
        total = payload.get("meta", {}).get("total-pages", 1)
        if page >= total:
            break
        page += 1
        if page > 50:
            raise ValueError("Treasury pagination budget exceeded")
    frame = pd.DataFrame(rows)
    balance_columns = [c for c in frame.columns if c.endswith("_bal") or c.startswith("close_today")]
    keep = ["record_date", "account_type", *balance_columns]
    frame = frame[keep].copy()
    for column in balance_columns:
        frame[column] = pd.to_numeric(frame[column].replace("null", None), errors="coerce")
    frame = frame.drop_duplicates(["record_date", "account_type"], keep="last")
    frame["available_at"] = _after_bdays(frame.record_date, 2).astype(str)
    # Account-type labels changed in 2021 (TGA restructuring); the series is
    # not continuous without a documented mapping, so it is context only.
    frame["pit_eligible"] = False
    raw = b"[" + b",".join(raw_pages) + b"]"
    return [archive.record("treasury", "dts_operating_cash", raw, frame, ["record_date", "account_type"],
                           {"url": url, "credibility": OFFICIAL, "pages": len(raw_pages),
                            "availability_rule": "+2 business days 22:00 UTC (DTS posts next business day ~16:00 ET)",
                            "pit_eligible": False, "first": frame.record_date.min(), "last": frame.record_date.max(),
                            "limitation": "account-type taxonomy changed 2021; context only until mapped"},
                           balance_columns)]


def collect_sec(client, archive, tickers=SEC_TICKERS):
    response = client.get("https://www.sec.gov/files/company_tickers.json")
    directory = {v["ticker"]: int(v["cik_str"]) for v in json.loads(response.content).values()}
    rows, raws = [], []
    for ticker in tickers:
        cik = directory[ticker]
        blocks = []
        sub = client.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        raws.append(sub.content)
        payload = json.loads(sub.content)
        blocks.append(payload["filings"]["recent"])
        for extra in payload["filings"].get("files", [])[:10]:
            more = client.get(f"https://data.sec.gov/submissions/{extra['name']}")
            raws.append(more.content)
            blocks.append(json.loads(more.content))
        for block in blocks:
            for i, form in enumerate(block["form"]):
                if form not in SEC_FORMS:
                    continue
                accepted = block["acceptanceDateTime"][i]
                rows.append({"ticker": ticker, "cik": cik, "accession": block["accessionNumber"][i], "form": form,
                             "filing_date": block["filingDate"][i], "report_date": block["reportDate"][i] or None,
                             # EDGAR acceptance timestamps are US Eastern wall-clock time.
                             "available_at": pd.Timestamp(accepted[:19]).tz_localize("America/New_York").tz_convert("UTC").isoformat(),
                             "items": block.get("items", [""] * len(block["form"]))[i] or None})
    frame = pd.DataFrame(rows).drop_duplicates("accession")
    frame["event_type"] = frame.form.map({"10-K": "ANNUAL_REPORT", "10-Q": "QUARTERLY_REPORT", "8-K": "CURRENT_REPORT"})
    frame["pit_eligible"] = True
    raw = gzip.compress(b"\n".join(raws), mtime=0)
    return [archive.record("sec", "megacap_filings", raw, frame, ["accession"],
                           {"url": "https://data.sec.gov/submissions/", "credibility": OFFICIAL,
                            "tickers": list(tickers), "availability_rule": "EDGAR acceptanceDateTime (exact)",
                            "pit_eligible": True, "first": frame.filing_date.min(), "last": frame.filing_date.max(),
                            "limitation": "ticker set is today's megacaps: survivorship-biased membership"},
                           ["form", "filing_date", "available_at"])]


def classify_fed(title):
    for event_type, pattern in FED_EVENT_RULES:
        if re.search(pattern, title):
            return event_type
    return "OTHER_PRESS_RELEASE"


def collect_fed(client, archive):
    response = client.get("https://www.federalreserve.gov/feeds/press_all.xml", access="crawl")
    root = ET.fromstring(response.content.decode("utf-8-sig"))
    rows = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        published = parsedate_to_datetime(item.findtext("pubDate")).astimezone(UTC)
        rows.append({"link": (item.findtext("link") or "").strip(), "title": title,
                     "category": (item.findtext("category") or "").strip(),
                     "published_at": published.isoformat(), "available_at": published.isoformat(),
                     "event_type": classify_fed(title), "affected_instruments": "NQ;ES;ZN" if "FOMC" in classify_fed(title) or classify_fed(title) == "MONETARY_POLICY" else "",
                     "extraction": "rule-based title classification; no LLM"})
    frame = pd.DataFrame(rows)
    return [archive.record("fed", "press_releases", response.content, frame, ["link"],
                           {"url": response.url, "credibility": OFFICIAL, "pit_eligible": False,
                            "availability_rule": "RSS pubDate", "first": frame.published_at.min(), "last": frame.published_at.max(),
                            "limitation": "feed holds recent items only; forward event context, no backtest history"},
                           ["title", "event_type"])]


def collect_gdelt(client, archive, timespan="7d"):
    entries = []
    for name, query in GDELT_QUERIES.items():
        response = client.get("https://api.gdeltproject.org/api/v2/doc/doc",
                              params={"query": f"{query} sourcelang:english", "mode": "artlist", "maxrecords": 75,
                                      "format": "json", "timespan": timespan, "sort": "datedesc"})
        articles = json.loads(response.content or b"{}").get("articles", [])
        frame = pd.DataFrame([{"url": a["url"], "title": a.get("title"), "domain": a.get("domain"),
                               "source_country": a.get("sourcecountry"),
                               "seen_at": pd.to_datetime(a["seendate"], utc=True).isoformat(),
                               "available_at": pd.to_datetime(a["seendate"], utc=True).isoformat(),
                               "query": name} for a in articles],
                             columns=["url", "title", "domain", "source_country", "seen_at", "available_at", "query"])
        frame = frame.drop_duplicates("url")
        entries.append(archive.record("gdelt", name, response.content, frame, ["url"],
                                      {"url": response.url, "credibility": AGGREGATOR, "pit_eligible": False,
                                       "availability_rule": "GDELT seendate (first crawl), not original publication",
                                       "first": frame.seen_at.min() if len(frame) else None,
                                       "last": frame.seen_at.max() if len(frame) else None,
                                       "limitation": "article metadata only (no full text stored); rolling 3-month API window"},
                                      ["title"]))
    return entries


def collect_bls(client, archive, start_year=None):
    # Reuse the existing adapter; keyless v2 allows 10-year windows.
    end_year = datetime.now(UTC).year
    start_year = start_year or end_year - 9
    result = bls_adapter.fetch_series(list(bls_adapter.SERIES), start_year, end_year, transport=_PostShim(client))
    frame = pd.DataFrame(result["rows"])[["series", "date", "value", "period"]]
    frame["available_at"] = None  # release clock times are not in this API response
    frame["pit_eligible"] = False
    raw = json.dumps(result, sort_keys=True, default=str).encode()
    return [archive.record("bls", "core_series", raw, frame, ["series", "date"],
                           {"url": bls_adapter.ENDPOINT, "credibility": OFFICIAL, "pit_eligible": False,
                            "availability_rule": "none: monthly period only, revised; needs release calendar + vintages",
                            "first": frame.date.min(), "last": frame.date.max()}, ["value"])]


class _PostShim:
    """Route the BLS adapter's POST through the polite client's spacing."""

    def __init__(self, client):
        self.client = client

    def post(self, url, json=None, timeout=None):
        self.client._wait(self.client._domain(url))
        return self.client.session.post(url, json=json, timeout=timeout,
                                        headers={"User-Agent": "NocturneFutures-research/3U"})


YAHOO_FUTURES = {"NQ=F": "NQ", "ES=F": "ES"}
# Free Yahoo windows: 1m only for the last ~30 days in <=8-day requests.
# range=max silently downsamples daily bars to monthly; use explicit epoch bounds.
YAHOO_INTERVALS = {"1d": {"period1": 946684800}, "60m": {"range": "730d"}, "5m": {"range": "60d"}}


def parse_yahoo_chart(payload: bytes, symbol: str, interval_seconds: int, now=None):
    """Complete bars only; a bar with any missing OHLC field is dropped, never imputed."""
    result = json.loads(payload)["chart"]["result"][0]
    if result["meta"]["symbol"] != symbol:
        raise ValueError("Yahoo symbol identity mismatch")
    quote = result["indicators"]["quote"][0]
    frame = pd.DataFrame({"timestamp": pd.to_datetime(result.get("timestamp", []), unit="s", utc=True),
                          **{k: quote[k] for k in ("open", "high", "low", "close", "volume")}})
    now = now or pd.Timestamp.now(tz="UTC")
    frame["available_at"] = frame.timestamp + pd.Timedelta(seconds=interval_seconds)
    dropped = int(frame[["open", "high", "low", "close"]].isna().any(axis=1).sum())
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame = frame[frame.available_at <= now]
    if interval_seconds < 86400:
        # Yahoo appends a live partial bar stamped at the last tick; keep aligned bars only.
        epoch = (frame.timestamp - pd.Timestamp(0, tz="UTC")).dt.total_seconds().round().astype("int64")
        frame = frame[epoch % interval_seconds == 0]
    frame["volume"] = frame.volume.fillna(0)
    frame = frame.drop_duplicates("timestamp", keep="last")
    bad = (frame.high < frame[["open", "close", "low"]].max(axis=1)) | (frame.low > frame[["open", "close", "high"]].min(axis=1))
    frame = frame.assign(timestamp=frame.timestamp.astype(str), available_at=frame.available_at.astype(str),
                         ohlc_consistent=~bad, contract_id="CONTINUOUS_FRONT_UNADJUSTED")
    return frame, {"dropped_incomplete_bars": dropped, "inconsistent_bars": int(bad.sum()),
                   "exchange_timezone": result["meta"].get("exchangeTimezoneName")}


def collect_yahoo_futures(client, archive, intervals=None):
    entries = []
    seconds = {"1d": 86400, "60m": 3600, "5m": 300, "1m": 60}
    for symbol, root in YAHOO_FUTURES.items():
        for interval in intervals or [*YAHOO_INTERVALS, "1m"]:
            if interval == "1m":
                now = pd.Timestamp.now(tz="UTC")
                chunks = [(now - pd.Timedelta(days=d + 7), now - pd.Timedelta(days=d)) for d in (0, 7, 14, 21)]
                frames, raws, meta = [], [], {"dropped_incomplete_bars": 0, "inconsistent_bars": 0}
                for start, end in chunks:
                    r = client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
                                   params={"interval": "1m", "period1": int(start.timestamp()), "period2": int(end.timestamp())})
                    f, m = parse_yahoo_chart(r.content, symbol, 60)
                    frames.append(f), raws.append(r.content)
                    meta = {k: meta[k] + m[k] for k in ("dropped_incomplete_bars", "inconsistent_bars")} | {"exchange_timezone": m["exchange_timezone"]}
                frame = pd.concat(frames).drop_duplicates("timestamp", keep="last")
                raw = b"[" + b",".join(raws) + b"]"
                url = "chart?interval=1m (4 x 7-day windows)"
            else:
                r = client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
                               params={"interval": interval, **YAHOO_INTERVALS[interval],
                                       **({"period2": int(pd.Timestamp.now(tz="UTC").timestamp())} if interval == "1d" else {})})
                frame, meta = parse_yahoo_chart(r.content, symbol, seconds[interval])
                raw, url = r.content, r.url
            entries.append(archive.record("yahoo_futures", f"{root}_{interval}", raw, frame, ["timestamp"],
                                          {"url": url, "credibility": UNOFFICIAL, "pit_eligible": True,
                                           "availability_rule": "bar end (lower bound; dissemination latency unknown)",
                                           "first": frame.timestamp.min(), "last": frame.timestamp.max(),
                                           "limitation": "continuous front-month, unadjusted, Yahoo roll schedule; not raw contracts",
                                           **meta}, ["open", "high", "low", "close", "volume"]))
    return entries


BLOCKED_SOURCES = {
    "eia": {"status": "BLOCKED_KEY_REQUIRED", "evidence": "api.eia.gov returned 403 API_KEY_MISSING", "credential_env": "EIA_API_KEY"},
    "bea": {"status": "BLOCKED_KEY_REQUIRED", "evidence": "apps.bea.gov API requires UserID registration; keyless request returned empty body", "credential_env": "BEA_API_KEY"},
    "nasdaq_data_link": {"status": "BLOCKED_KEY_REQUIRED", "evidence": "dataset access needs NASDAQ_DATA_LINK_API_KEY; premium index feeds not free", "credential_env": "NASDAQ_DATA_LINK_API_KEY"},
    "nasdaq_web_api": {"status": "NOT_USED_UNOFFICIAL_UNAVAILABLE", "evidence": "api.nasdaq.com timed out from this host; undocumented site API without published terms"},
    "forexfactory": {"status": "NOT_CRAWLED_TERMS_UNVERIFIED", "evidence": "robots.txt permits, but permission for automated collection in site terms was not verified; official Fed/BLS sources used instead"},
    "bloomberg_reuters": {"status": "LICENSED_NOT_ACCESSED", "evidence": "paywalled/licensed; no bypass"},
    "databento": {"status": "FUTURES_DATA_BLOCKED", "evidence": "DATABENTO_API_KEY absent; USER_ACTION_REQUIRED"},
}

COLLECTORS = {"yahoo_futures": collect_yahoo_futures, "fred": collect_fred, "cftc": collect_cftc, "treasury": collect_treasury, "sec": collect_sec,
              "fed": collect_fed, "gdelt": collect_gdelt, "bls": collect_bls}
INTERVALS = {"query2.finance.yahoo.com": 2.0, "fred.stlouisfed.org": 1.0, "publicreporting.cftc.gov": 1.0, "api.fiscaldata.treasury.gov": 0.5,
             "www.sec.gov": 0.2, "data.sec.gov": 0.2, "www.federalreserve.gov": 1.0,
             "api.gdeltproject.org": 6.0, "api.bls.gov": 2.0}
