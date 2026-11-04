# Futures data requirements

No licensed futures data is present in this environment. `DATABENTO_API_KEY` is
unset, so the adapter is fixture-tested only and no real download has occurred.
This document states exactly what is required to advance NQ/ES target research.

## Required entitlement

| Item | Requirement |
|---|---|
| Provider | Databento |
| Dataset | `GLBX.MDP3` (CME Globex MDP 3.0) |
| Schemas | `ohlcv-1m`, `trades`, `bbo-1s` or `bbo-1m`, `mbp-1`, `mbp-10`, `mbo` (only as entitled) |
| Symbol type | `raw_symbol`, one explicit contract per request |
| Instruments | NQ, MNQ, ES, MES, ZN, ZB; VX requires the CFE dataset |
| History | Multi-year, contract-specific; continuous symbols are research context only |
| Licensing | Exchange fees and redistribution terms per the provider agreement |

The adapter already enforces one raw contract per request, daily chunking, raw
byte checksums, normalized exports, revision rejection and resumable downloads.
It does not infer rolls, back-adjust prices or fill missing bars.

## Exact commands

```powershell
$env:DATABENTO_API_KEY = "<key>"
python scripts/phase3e_providers.py databento `
  --contract NQH5 --instrument NQ `
  --start 2025-01-02T00:00:00Z --end 2025-01-03T00:00:00Z `
  --license-scope "<license reference>"
```

Before a bulk download, query the provider's billable-size and cost endpoints for
the exact date range. Cost is entitlement- and volume-dependent and is not
estimated here.

## Validation that must pass before modeling

1. Contract identity: one `instrument_id`/symbol per request; no mixing.
2. Rolls: explicit roll dates and separate raw contracts; never stitched silently.
3. Session grid: exchange holidays and early closes from an authoritative calendar.
4. Duplicates: none on `(contract_id, timestamp)`.
5. Timestamps: UTC event time plus a documented availability bound.
6. Prices: raw versus adjusted stated explicitly; tick size matches the contract.
7. Quotes: bid <= ask, no crossed books, sequence gaps reported.
8. Depth: sequence numbers monotonic; gaps recorded, never interpolated.

## What remains blocked without it

- NQ/ES contract-level 1m/5m feature and target research beyond the 60-day cache.
- Authentic trades, volume-at-price, cumulative delta, absorption and book features.
- Actual VX futures; `^VIX` is only a spot proxy.
- Multi-year intraday target-before-stop and time-to-target estimates.

Free daily index and ETF history cannot substitute for these. Index levels are not
tradable and their session ranges differ from futures ranges.
