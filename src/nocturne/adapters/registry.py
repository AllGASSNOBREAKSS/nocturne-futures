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
        instruments=("DGS10", "DGS2", "DFF", "CPIAUCSL", "UNRATE"),
    ),
    Provider(
        name="bls", category="macro", access="FREE_OFFICIAL", credential_env="BLS_API_KEY",
        implemented=True, verified_with_real_data=False,
        coverage="CPI, PPI, employment and wages series; multi-decade.",
        limits="Registration key raises limits; without a key the public API is "
               "heavily throttled.",
        license_note="Public domain US government data.",
        endpoints=("https://api.bls.gov/publicAPI/v2/timeseries/data/",),
        instruments=("CUUR0000SA0", "WPUFD4", "CES0000000001", "LNS14000000"),
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
