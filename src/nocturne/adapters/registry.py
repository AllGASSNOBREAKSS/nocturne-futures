"""Declarative provider registry with explicit access status.

Status vocabulary:
  FREE_OFFICIAL      official API, free registration or no key
  FREE_UNOFFICIAL    public endpoint without a supported API contract
  FREEMIUM           free tier with documented limits
  LICENSED           requires a paid entitlement
  BLOCKED            no credential or entitlement present in this environment
  NOT_IMPLEMENTED    no adapter written

The registry never stores credentials and never asserts that an integration works
without a verified response.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Provider:
    name: str
    category: str
    access: str
    credential_env: str | None
    implemented: bool
    verified_with_real_data: bool
    coverage: str
    limits: str
    license_note: str
    endpoints: tuple[str, ...] = field(default_factory=tuple)
    instruments: tuple[str, ...] = field(default_factory=tuple)


PROVIDERS = (
    Provider(
        name="yahoo_chart", category="market_bars", access="FREE_UNOFFICIAL",
        credential_env=None, implemented=True, verified_with_real_data=True,
        coverage="Daily: ^GSPC from 1927, ^NDX from 1985, ^VIX from 1990, QQQ 1999+, "
                 "SPY 1993+, TLT 2002+, continuous NQ/ES proxies 2000+. Intraday: "
                 "60 days of 5m, two years of 1h.",
        limits="Unofficial endpoint; rate-limited; occasional invalid futures prints; "
               "no supported SLA.",
        license_note="Public research use subject to Yahoo terms. Not a production "
                     "exchange feed. Not for redistribution.",
        endpoints=("https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",),
        instruments=("^GSPC", "^NDX", "^VIX", "QQQ", "SPY", "TLT", "^TNX", "NQ=F", "ES=F"),
    ),
    Provider(
        name="fred", category="macro", access="FREE_OFFICIAL", credential_env="FRED_API_KEY",
        implemented=True, verified_with_real_data=True,
        coverage="Official series from 1986 in the committed snapshot; API supports "
                 "full history and real-time vintages.",
        limits="Latest-vintage CSV needs no key; ALFRED vintages require a free key.",
        license_note="Federal Reserve Bank of St. Louis terms; cite the source.",
        endpoints=("https://fred.stlouisfed.org/graph/fredgraph.csv",
                   "https://api.stlouisfed.org/fred/series/observations"),
         instruments=("DGS10", "DGS2", "DFF", "CPIAUCSL", "UNRATE", "NASDAQ100"),
    ),
    Provider(
        name="bls", category="macro", access="FREE_OFFICIAL", credential_env="BLS_API_KEY",
        implemented=True, verified_with_real_data=True,
        coverage="CPI, PPI, employment and wages series; multi-decade.",
        limits="Registration key raises limits; without a key the public API is "
               "heavily throttled.",
        license_note="Public domain US government data.",
        endpoints=("https://api.bls.gov/publicAPI/v2/timeseries/data/",),
        instruments=("CUUR0000SA0", "WPUFD4", "CES0000000001", "LNS14000000"),
    ),
    # Phase 3U keyless official sources, collected by nocturne.collector.
    Provider(
        name="cftc_cot", category="positioning", access="FREE_OFFICIAL", credential_env=None,
        implemented=True, verified_with_real_data=True,
        coverage="Traders in Financial Futures (futures-only) for E-mini Nasdaq-100, E-mini S&P 500, "
                 "2y/10y T-notes, 2006-06 onward; weekly Tuesday positions.",
        limits="Socrata public API; released Fridays 15:30 ET, delayed during government shutdowns.",
        license_note="Public US government data.",
        endpoints=("https://publicreporting.cftc.gov/resource/gpe5-46if.json",),
        instruments=("209742", "13874A", "043602", "042601"),
    ),
    Provider(
        name="treasury_fiscaldata", category="fiscal_liquidity", access="FREE_OFFICIAL", credential_env=None,
        implemented=True, verified_with_real_data=True,
        coverage="Daily Treasury Statement operating cash balance (TGA), 2005-10 onward.",
        limits="Documented public API; account taxonomy changed in 2021 (context only).",
        license_note="Public US government data.",
        endpoints=("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance",),
    ),
    Provider(
        name="sec_edgar", category="corporate_filings", access="FREE_OFFICIAL", credential_env=None,
        implemented=True, verified_with_real_data=True,
        coverage="10-K/10-Q/8-K submission metadata with exact acceptance times for ten Nasdaq megacaps.",
        limits="SEC fair access: declared User-Agent, <=10 requests/second (collector uses 5/s).",
        license_note="Public EDGAR data; filing text not redistributed.",
        endpoints=("https://www.sec.gov/files/company_tickers.json", "https://data.sec.gov/submissions/"),
    ),
    Provider(
        name="fed_press", category="events", access="FREE_OFFICIAL", credential_env=None,
        implemented=True, verified_with_real_data=True,
        coverage="Federal Reserve Board press-release RSS (recent ~20 items), rule-classified events.",
        limits="Feed is recent-only; forward context, not backtest history.",
        license_note="Public US government content.",
        endpoints=("https://www.federalreserve.gov/feeds/press_all.xml",),
    ),
    Provider(
        name="gdelt_doc", category="news_metadata", access="FREE_UNOFFICIAL", credential_env=None,
        implemented=True, verified_with_real_data=False,
        coverage="Article metadata (title/url/domain/seen time), rolling ~3 months.",
        limits="One request per 5 seconds; this host received HTTP 429 during Phase 3U.",
        license_note="GDELT open data terms; media content not stored.",
        endpoints=("https://api.gdeltproject.org/api/v2/doc/doc",),
    ),
    Provider(
        name="eia", category="energy", access="FREE_OFFICIAL", credential_env="EIA_API_KEY",
        implemented=False, verified_with_real_data=False,
        coverage="Energy prices and inventories.", limits="Free key required (403 API_KEY_MISSING without).",
        license_note="Public US government data.", endpoints=("https://api.eia.gov/v2/",),
    ),
    Provider(
        name="bea", category="macro", access="FREE_OFFICIAL", credential_env="BEA_API_KEY",
        implemented=False, verified_with_real_data=False,
        coverage="GDP, PCE, personal income.", limits="Free UserID registration required.",
        license_note="Public US government data.", endpoints=("https://apps.bea.gov/api/data",),
    ),
    Provider(
        name="databento", category="futures_intraday", access="LICENSED",
        credential_env="DATABENTO_API_KEY", implemented=True, verified_with_real_data=False,
        coverage="CME GLBX raw-contract OHLCV, trades, MBP/MBO depending on entitlement.",
        limits="Usage-based billing; entitlement required per dataset.",
        license_note="Exchange fees and redistribution terms apply.",
        endpoints=("https://hist.databento.com/v0/timeseries.get_range",),
        instruments=("NQ", "MNQ", "ES", "MES", "ZN", "ZB", "VX"),
    ),
    Provider(
        name="nasdaq_data_link", category="market_bars_macro", access="FREEMIUM",
        credential_env="NASDAQ_DATA_LINK_API_KEY", implemented=False,
        verified_with_real_data=False,
        coverage="Dataset-dependent. Free datasets exist; premium feeds are not free.",
        limits="Per-dataset access rights, rate limits and cost must be verified "
               "before ingestion.",
        license_note="Do not assume premium Nasdaq feeds are free.",
        endpoints=("https://data.nasdaq.com/api/v3/datasets/{vendor}/{dataset}.json",),
        instruments=(),
    ),
    Provider(
        name="bloomberg_blpapi", category="news_reference", access="LICENSED",
        credential_env="BLOOMBERG_BLPAPI_ENABLED", implemented=False,
        verified_with_real_data=False,
        coverage="Terminal-entitled reference, news and market data.",
        limits="Requires an installed Terminal and licensed entitlements.",
        license_note="No paywall bypass; no website scraping.",
        endpoints=(),
        instruments=(),
    ),
)


def status(provider: Provider) -> str:
    if not provider.implemented:
        return "NOT_IMPLEMENTED"
    if provider.access == "FREE_OFFICIAL":
        return "AVAILABLE" if provider.credential_env and os.environ.get(provider.credential_env) \
            else "AVAILABLE_NO_KEY"
    if provider.access in {"LICENSED", "FREEMIUM"}:
        if provider.credential_env and not os.environ.get(provider.credential_env):
            return "BLOCKED"
        return "ENTITLEMENT_UNVERIFIED"
    if not provider.verified_with_real_data:
        return "IMPLEMENTED_UNVERIFIED"
    return "AVAILABLE"


def registry() -> dict:
    entries = []
    for provider in PROVIDERS:
        entry = asdict(provider)
        entry["status"] = status(provider)
        entry["credential_present"] = bool(provider.credential_env and os.environ.get(provider.credential_env))
        entries.append(entry)
    return {"providers": entries,
            "secrets_policy": "environment variables only; never committed or logged",
            "free_first": [p.name for p in PROVIDERS if p.access.startswith("FREE")],
            "paid_dependencies": [p.name for p in PROVIDERS if p.access == "LICENSED"]}
