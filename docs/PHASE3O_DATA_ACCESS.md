# Futures access — final actionable blocker

Status at Phase 3O: **BLOCKED / zero licensed rows**. Databento key absent in
process, Windows user and machine scopes. No authenticated request or paid data
consumption was attempted. Cost/entitled range/resolved IDs/credit eligibility
remain unknown. A missing credential is not a software failure or a successful
zero-trade backtest.

## Operator checklist

1. Under an authorized Databento account, verify **GLBX.MDP3 / CME Globex** access,
   historical license, exchange fees and any actual credit balance/eligibility.
2. Configure `DATABENTO_API_KEY` locally through an approved secret mechanism;
   do not send it in chat, logs, command history or Git.
3. Run `python scripts/phase3n_futures.py --research-check` for free metadata and
   symbology only. With no key it makes no authenticated calls and exits blocked.
4. Review actual schema range/conditions, raw contract mapping and provider
   count/billable bytes/USD quote. Proposed pilot: **NQZ6**, **ESZ6**, separately,
   `2026-11-01T23:00:00Z` through exclusive `2026-11-02T22:00:00Z`, `ohlcv-1m`.
   Candidates are not claimed provider-resolved contracts without that check.
5. Obtain explicit user approval of each exact quote and budget, including any
   credit/zero-price consumption, then supply the local quote/approval files to
   the existing downloader. The agent creates no approved file automatically.
6. Validate hashes, ID, UTC/DST/session grids, ticks, integer volume, duplicates,
   gaps, availability/roll provenance and complete 5m aggregation before research.
   Missing minute messages are not filled. A one-session pilot proves plumbing,
   not predictive power or historical PIT publication times.

At most 2,760 planned minute slots under the two 23-hour-session assumption;
this is not an actual row count, binary size or cost quote. An expected USD
amount cannot be honestly supplied without authenticated provider sizing.

After approved bars: separately quote/authorize `trades`, `tbbo`/`mbp-1`, then
`mbp-10`/`mbo` only as entitled. True volume-at-price/CVD needs trades and side
semantics; bid/ask/depth needs quote and sequence/reconstruction validation.
No OHLCV-derived proxy is substituted for those inputs. Existing byte limits,
quote freshness, cost checks, durable reservations and no-blind-retry controls
remain enforced. A quoted budget is not a provider-enforced final invoice cap.

Exact existing approval/CLI details: `PHASE3N_DATA_DECISION.md`. Private receipts,
approval objects and snapshots require authorized backup; a clone is insufficient.
Until access is configured, do not keep attempting downloads or train more models
on the same inadequate context. Keep **NO_PROMOTION / NO_TRADE**.
