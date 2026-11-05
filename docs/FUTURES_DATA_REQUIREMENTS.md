# Futures data requirements

No licensed futures data is present in this environment. `DATABENTO_API_KEY` is
unset, so the adapter is fixture-tested only and no real download has occurred.
This document states exactly what is required to advance NQ/ES target research.

**Phase 3N guard:** current decision and operator steps are in
`PHASE3N_DATA_DECISION.md`. Every new metered request needs a fresh authenticated
quote and explicit approval, including promotional-credit usage. Existing report
fields remain null until actual provider access is established.

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

The adapter enforces one raw NQ/ES contract per request, at most one day per
approved pilot, raw byte checksums, normalized exports and local receipt reuse.
Uncertain streaming attempts require operator reconciliation, not blind retries.
It does not infer rolls, back-adjust prices or fill missing bars.

## Exact commands

```powershell
python scripts/phase3n_futures.py --public-docs --research-check
# After reviewing actual quotes and obtaining explicit consumption authorization:
python scripts/phase3e_providers.py databento `
  --contract NQZ6 --instrument NQ `
  --start 2026-11-01T23:00:00Z --end 2026-11-02T22:00:00Z `
  --license-scope "<actual license reference>" `
  --quote "<saved quote.json>" --approval "<authorized approval.json>"
```

Before a bulk download, query the provider's billable-size and cost endpoints for
the exact date range. Cost is entitlement- and volume-dependent and is not
estimated here.
Bulk acquisition is not authorized or implemented by the guarded pilot command.
Configure secrets locally through an approved mechanism, not in chat or committed
scripts. Provider quotes are estimates, not guaranteed final-invoice ceilings.

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

## Explicit storage-planning estimate (not observed data or a cost quote)

Assume 252 sessions/year, 23 hours/session, NQ and ES, and one active raw contract
per instrument. This gives at most 695,520 one-minute rows and 139,104 five-minute
rows under those assumptions. At an assumed 150–250 CSV bytes/row, one-minute
exports are about 104–174 MB/year total and derived five-minute exports about
21–35 MB/year, uncompressed. Roll overlap, shortened sessions, actual calendars,
provider encoding and retained raw responses change storage substantially.

These are engineering planning assumptions, not a downloaded sample, exact
exchange schedule or provider billable volume. Trades, quotes, depth and MBO
cannot be sized honestly from OHLCV; request provider metadata/size/cost for the
exact bounded contract, schema and dates after entitlement is configured. Do not
purchase or initiate a bulk download from this estimate. `phase3i_readiness.py`
reports the assumptions and derived byte ranges separately from readiness.

## Phase 3L: concrete bounded pilot and minimum coverage

Readiness: `reports/phase3l_readiness.json`. No Databento credential exists in
process, user or machine scope, and no authenticated size/cost quote or download
was attempted. Cost is unknown, not zero; obtain a quote and entitlement before
billable access. Never paste credentials into prompts or logs.

An ordinary full-session plumbing pilot is NQZ6 and ESZ6 separately, from
`2026-11-01T23:00:00Z` to `2026-11-02T22:00:00Z`, schema `ohlcv-1m`, raw symbols.
Under a 23-hour-session assumption this is at most 1,380 minute rows per contract,
2,760 total. It validates engineering, not predictive power. Use the existing
`phase3e_providers.py databento` command with these explicit contract/date bounds
only after authorized configuration and provider sizing/cost review.

Research should seek 3+ years across contracts and regimes with disjoint
training/calibration/holdout periods and sufficient independent event counts;
calendar years alone do not establish an adequate dataset or accuracy.

`phase3l_contract_replay.py` verifies private request/receipt/raw/export lineage
before replay. Historical bar-end availability is only a lower bound; it is not
proof of dissemination latency, release vintage or authoritative session/roll
coverage. Resolve those before promotion. Trades/quotes and depth/MBO each need
their own licensed schemas, sizing and sequencing/side-semantics validation.
