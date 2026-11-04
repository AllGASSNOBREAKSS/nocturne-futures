# Data providers

Status is recorded by `adapters/registry.py` and printed by
`python scripts/phase3g_providers.py`. Credentials are read from environment
variables only. Never commit keys, tokens or account identifiers.

## Verified in this environment

### Yahoo Finance chart endpoint (free, unofficial)

- Used for daily index, ETF and continuous-futures-proxy history, plus two years of
  hourly and about 60 days of five-minute NQ/ES bars.
- No API key. Unofficial, rate-limited and occasionally returns invalid futures
  prints; the adapter drops invalid OHLC rows instead of repairing them.
- Coverage: `reports/phase3g_coverage.json`.
- Not a production exchange feed and not suitable for redistribution.

### FRED (official, free)

- Latest-vintage CSV needs no key. ALFRED real-time vintages need a free key:
  `FRED_API_KEY`.
- Existing snapshots: `data/history/fred/`.
- Revised values are excluded from historical features without a release/vintage
  timestamp.

### BLS (official, free)

- `https://api.bls.gov/publicAPI/v2/timeseries/data/`
- Works without a key at reduced limits; `BLS_API_KEY` raises them.
- The adapter rejects unapproved series, skips annual averages and preserves `-`
  as a missing value rather than zero.
- Values are monthly and do not include a release timestamp or consensus, so they
  are not point-in-time eligible.

## Licensed or blocked

### Databento (paid entitlement)

- `DATABENTO_API_KEY`, dataset `GLBX.MDP3`, raw contracts only.
- Adapter implemented and fixture-tested; no credential was present, so no real
  download occurred.
- Pricing is usage-based; query the provider's billable-size and cost endpoints
  before downloading. Do not estimate cost from row counts alone.

### Nasdaq Data Link (freemium)

- `NASDAQ_DATA_LINK_API_KEY`.
- Adapter not implemented. Per-dataset rights, coverage and cost must be verified
  first; premium feeds are not assumed free.

### Bloomberg (licensed)

- Requires a Terminal and BLPAPI entitlement. No adapter. Website access does not
  grant API rights and paywalls are not bypassed.

## Local history separation

Index levels, ETFs, futures proxies and rates are stored separately under
`data/history/yahoo_daily/normalized/`. Continuous futures proxies are never
treated as raw contracts. Contract-level intraday history remains blocked.
