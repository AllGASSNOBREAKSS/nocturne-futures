# Phase 3N — guarded acquisition and contract diagnostic integration

Checkpoint: 2026-11-05 UTC. Branch `feat/phase3n`, base `2dcec42`.
Trading remains **NO_TRADE**, promotion **NO_PROMOTION**. No frontend changes.

## Verified previous phase

HEAD was `2dcec42`; Phase 3M CI was independently verified green for Python,
TypeScript, native and Windows-shadow:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41954993266

Scheduler-generated report modifications present on entry were retained. The
existing six-hour research and 30-minute shadow tasks initially had successful
inspected results. A later shadow failure is detailed below; it must not be hidden
by earlier successes. No task principal, credential, security setting or schedule
was changed.

## Highest-priority result: data access is still blocked

Databento and the other known provider keys are absent from checked process,
Windows user and machine scopes. No authenticated metadata request, paid request,
subscription or historical download occurred. Both NQZ6 and ESZ6 inventories have
**zero licensed rows**; their actual orchestrated diagnostic jobs returned BLOCKED.

All supplied public URLs returned HTTP 200 and were hash-archived. The official
Historical API reference confirms free metadata/symbology, metered time series,
repeated streaming charges and the required metadata/cost endpoints. Public page
retrieval does not establish account eligibility for credits or a numeric quote.

**Actual cost, billable bytes, record count, entitled historical range, resolved
provider IDs and credit eligibility remain unknown/null.** Candidate raw symbols
are explicit proposed December contracts, not claimed provider-confirmed mappings.
One actionable decision/activation report is `PHASE3N_DATA_DECISION.md`; exact
machine evidence is `reports/phase3n_futures_access.json`. No guessed dollar amount
or fixture price is represented as a provider estimate.

## Implemented on the existing provider, not another data engine

`adapters/databento_access.py` queries only allowlisted free interfaces when a key
exists. It checks dataset/schema listing, entitled schema range, daily condition,
complete same-ID symbology, provider count/size/cost, and saves content-hashed
metadata evidence. It never invokes time-series/batch consumption.

The existing Databento bar downloader now requires a hash-bound, fresh quote and
explicit operator approval for the exact instrument/raw contract/schema/bounds,
within approved quoted-cost and billable-byte budgets. Even zero quoted cost or
credit use is not automatically authorized. The CLI requires both files.

Before network consumption, a per-request OS lock and durable reservation prevent
automatic duplicate charged requests after an uncertain result. Completed local
receipts remain reusable without another call. An interrupted/failed request
requires provider-usage review and new operator authorization, not silent retry.

The downloader preserves successful raw responses before schema checks, rejected
bodies and bounded partial prefixes, and separate consumption-review events.
New receipts retain quote, approval digest/object, resolved ID, byte count and
validation evidence. Normalization rejects unknown identity, provider-ID mismatch,
non-minute-aligned/out-of-order timestamps, duplicate messages, fractional/invalid
volume, invalid OHLC and tick violations. Changed quoted/observed row counts block
for source review. New receipt replay rechecks archived approval/quote bindings;
legacy receipts do not receive fabricated retrospective authorization.

Pilot acquisition is intentionally one NQ/ES raw contract, at most 24 hours, with
default 16 MiB decoded-response budget (maximum 64 MiB). This is not a Windows Job
Object/cgroup memory limit or provider-enforced invoice ceiling. Existing worker
timeouts, lower research priority and model/inference separation remain in place.

## Receipt-to-existing-engine path

`research/futures_pilot.py` consumes the existing verified receipt loader and uses
the existing `_signals`, `_run`, backtest configuration and target-label builder.
The Phase 3M raw-futures job now calls this diagnostic instead of unconditionally
blocking even after data appears. Scheduled research checks NQ and ES separately;
it never purchases data. Inventory/code identity prevents duplicate identical
futures jobs across dates and between the CLI and recurring scheduler. Old index
experiments are no longer enqueued by default: use `--index-diagnostics` only
for an explicit development diagnostic request; the existing model cache still
prevents retraining/rescoring unchanged experiments.

With a complete engineering-calendar RTH minute grid, this bounded path produces:
ORB and bar-VWAP strategy diagnostics; 1/3/4-tick cost sensitivity; actual engine
simulated fills, outcomes, bar-extreme MFE/MAE bounds, expectancy/profit-factor/
drawdown; average winners/losers;
yearly trade summaries; separate ambiguity/censoring-aware 60-minute target labels;
and receipt/dataset provenance. Contract grouping remains explicit.

The bar VWAP remains a typical-price proxy, not trade-derived VWAP. Regime is
UNCLASSIFIED and unsupported volatility/profile/order-flow context remains null.
Labels' 60-minute horizon is explicitly separate from each strategy's configured
trade-exit horizon. Sparse grids block rather than being forward filled. The
built-in bounded calendar is not newly certified exchange scheduling evidence.
The diagnostic uses one whole contract with full TP1 exit, not an impossible
half-contract scale-out. Its one-minute input and bar-count horizons are explicit,
not assumed equivalent to earlier five-minute strategy studies. Full-bar exit-bar
excursions are bounds rather than reconstructed intrabar paths. No diagnostic net
return is independently validated execution P&L.

## Versioned execution-cost arithmetic correction

Inspection found that legacy backtest entry fills already included slippage,
then cost deductions charged that entry slip again. Partial exits also charged
the full contract count per exit event instead of charging exited quantity.
These are arithmetic/convention defects, not evidence for or against an edge.

The same engine now supports explicit `cashflow-v2`, used by the new pilot:
one adverse slip in entry fill, one weighted adverse exit slip, and two commission
sides per entered contract. Gross dollars are fill-price P&L before fees; costs
are commissions because slippage is already in fills. Exit prices and net points
are consistent with that convention. Whole-contract exit quantities are required.
Long/short and partial-exit cashflows have analytic regression tests.

`legacy-v1` remains the explicit compatibility default for historical study
reproduction; old reports were not recomputed or silently changed. Each trade
records its accounting version. Do not mix these conventions or reuse old strategy
P&L as corrected evidence. Cashflow-v2 assumes stressed market exits on barrier
touch, not guaranteed limit fills or queue execution. Real slippage/fees/fill
behavior still need independent data and execution-assumption validation.

The complete path was tested on isolated synthetic fixtures, **not authentic
market research samples**. Actual NQ/ES jobs still block before signal generation.
True volume profiles, value migration, CVD, bid/ask/DOM/absorption, PIT macro and
depth sequencing remain data-blocked; no OHLCV substitution or duplicate engine
was introduced for them.

## Predictive and forward evidence

No new logistic/LightGBM/CatBoost, direction, target-survival or order-flow model
was fitted; no already-used holdout was rescored. Old index-context diagnostics
remain old development results, not independent futures performance. Target-first,
directional and survival probabilities stay null. Large total NDX range is not a
200–500-point NQ target-first opportunity.

The existing read-only shadow cycle was refreshed/evaluated without making up
an observation. State remains **2 issued / 1 verified matured / 1 pending**;
one legacy matured observation and zero corrected-inference matured observations.
November 5 remains pending until the November 6 00:00 UTC adapter bound and
verified completed data. All original forecast/outcome and model-weight bytes
remain unchanged; no predictions were backdated or repaired.

### New source incident observed on resume, November 5 afternoon

The scheduler opened durable alerts for pending forecast
`3db9c4cbd3a9cc5944db8437`: its issued November 4 reference close
**28437.166015625** differs from the refreshed Yahoo value **28437.169921875**.
The cycle correctly reports **AUDIT_BLOCKED / REFERENCE_CLOSE_MISMATCH**. The
first matured outcome still verifies against its archived evaluation snapshot;
that does not clear the second forecast's new reference incident.

Inspected last scheduled research result: **0**; last shadow result: **1**, with
the source-audit failure preserved. Open alerts were not deleted or resolved by
tolerance inflation. No automatic reconciliation or new denominator was applied.
Deliberate hash-bound source investigation is required before accepting a second
outcome. Overall operations are degraded, not continuously healthy. Research
reports now include a separately timestamped operations snapshot alongside the
matured-outcome audit so the two statuses cannot be confused.

## Operations, tests and recovery

API `/v1/data/futures-readiness` now includes an additive timestamped acquisition
snapshot; GET never queries or consumes provider data. Existing research reporting
and immutable private attempt history include the two blocked futures jobs.
Architecture: `ARCHITECTURE_PHASE3N.md` and a new named Forq frame. Readiness:
`BACKEND_READINESS.md`; no arbitrary completion percentage is assigned.

Local verification: **342 tests passed including native parity**, TypeScript
typecheck passed. Fixture tests include free-only metadata, missing credentials,
403 sanitation, partial resolution/degraded conditions, invalid cost, stale or
changed approval/quote, budget/zero-credit consent, no-network denial, no-blind-
retry, bounded stream prefixes, timestamp/volume/identity checks, sparse/full-grid
engine integration and DST. Existing recovery, timeout, holiday, source-revision,
survival and frozen-forecast regression tests remain in the suite. Actual host
restart/logout was not performed or claimed. Verify this branch's own CI after push.

Private evidence now also includes `data/licensed/databento_metadata/` and guarded
bar `approval_objects`, raw/partial objects and consumption events. Back these up
with receipt stores and SQLite consistently; Git alone cannot restore private
proofs. Never delete a consumption reservation to force a charged retry.

## Next precise milestone

An operator configures authorized GLBX.MDP3 access, verifies credit/license terms,
runs the metadata-only preflight and supplies explicit approval for the resulting
actual quote. Then ingest the two bounded sessions, validate identity/grid/calendar/
latency/roll evidence and run the existing diagnostic on authentic receipts.
Only after sufficient independent history/event counts should new feature-family
ablations, directional comparisons and target-survival fitting resume.

Always-on deployment still needs separately authorized unattended credentials,
logout/restart evidence and off-host monitoring/backup. Neither sleeping/offline
hardware nor infrastructure tests establish continuous availability or predictive
skill. No paid infrastructure or security change was made.
