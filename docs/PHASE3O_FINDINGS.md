# Phase 3O — evidence-bound recovery and operational classification

Checkpoint: 2026-11-05 UTC. Branch `feat/phase3o`, base `8065a34`.
No frontend, paid infrastructure, subscriptions or live execution.
**NO_PROMOTION / NO_TRADE** remains enforced.

## Starting verification

Phase 3N's 342 tests, including native parity, reproduced locally. Its four CI
jobs were verified successful:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/42097502509
Pre-existing scheduler report changes were preserved, not reset.

`CYCLE_UNHEALTHY` and `FORECAST_AUDIT:3db9c4cbd3a9cc5944db8437` were real
source-integrity gates, not a crashed training worker or missing Databento key.
The shadow task was executing regularly and correctly returning 1 while blocked.
Research continued independently; unavailable licensed data remained BLOCKED.

## Deliberate reconciliation, not a replacement prediction

Forecast `3db9c4cbd3a9cc5944db8437` was issued at
`2026-11-05T00:17:12.620017+00:00`, with feature asof
`00:17:10.441833+00:00`. Canonical issued forecast hash:
`86169b61e5ed6c944b0c7fc617f810740c031510b79739524a88920c52df0e57`.
Its record seal and exact archived features/dataset digest reproduced.

Issuance index snapshot:
`2bdadb4e3d17c80a4358eed656b475e0129bfc86dfd217695a9d9659f50f7ec0`,
received at `00:17:09.704122+00:00`; VIX issuance snapshot:
`689859ddb6cb20aceaa687509476af451bc0975b6d6bcfa79b255b61e7df60f9`.
Both source roles/receipt chronology are reverified by the existing verifier.

For the **November 4 reference session**, Yahoo changed:
- Open: 28346.80859375 → 28346.810546875.
- High: 28829.662109375 → 28829.66015625.
- Low: 28276.21875 → 28276.220703125.
- Close: 28437.166015625 → 28437.169921875.
- Volume: 1891980000 → 9953250000.

The upstream session timestamp, INDEX identity, New York timezone and daily
granularity match; quoted/adjusted closes agree within each archived version.
This is a genuine source-as-observed revision, not a changed forecast. Yahoo's
internal cause and authoritative exchange finality remain unconfirmed. Bounded
cross-checks returned FRED ReadTimeout and Nasdaq HTTP 404; neither is corroboration.

`investigate_revision` uses embedded issuance snapshot IDs and verifies the
forecast seal, exact issuance inputs, current raw/normalized hashes, chronology,
unique session timestamp and measurement conventions. The new CLI defaults to
investigate-only; explicit `--apply` appends a separate proof. It never writes
forecasts or outcomes. Repeating an unchanged application reuses the proof.

The decision is **VERIFIED_AS_ISSUED_PROVIDER_REVISION**, under the existing
unofficial research-grade contract. The issued denominator **28437.166015625**
and quantiles remain unchanged. New proofs seal the entire revised reference
bar, not only its close. A later OHLCV change, missing/corrupt evidence or altered
forecast must block again; tests exercise a same-close/different-volume revision.
Legacy proofs retain their pre-existing validation policy rather than being
silently rewritten. Details: `reports/phase3o_reconciliation.json`; all raw proof
objects remain in the private source archive.

## Actual recovery and forecast state

After appending the verified proof, the real read-only runner completed cycle,
independent outcome audit, report and monitor successfully. The alert journal
appended RESOLVED events; original OPEN events remain intact. Recovered source
warnings are visible rather than removed. No tolerance was widened.

As of this checkpoint: **2 issued / 1 verified matured / 1 pending**. The first
legacy outcome remains its original archived observation; it was not rescored
on later Yahoo highs/lows. Corrected-inference matured count is still zero.
November 5's completed bar is not eligible before November 6 00:00 UTC under
the adapter bound. Reconciliation does not itself create an outcome or prove
forward calibration. Forecast/outcome bytes and frozen model weights are intact.

## Confirmed software/reporting fixes

- `health()` previously considered only the last successful cycle and a 48-hour
  age threshold. A recent audit failure could therefore coexist with nested
  `status=ok`. It now exposes last attempt separately from last success and flags
  `LATEST_CYCLE_NOT_OK`; failure events cannot mask stale success.
- Operations retain existing incident keys and add component statuses with exact
  reasons: blocked source audit/data, failed refresh/process, degraded/stale
  evidence and healthy gate evaluation. Blocks are not silently relabeled success.
- Orchestrator dependencies on missing data or explicitly disabled jobs now use
  `DEPENDENCY_BLOCKED`; actual failed parents still use `DEPENDENCY_FAILED`.
  `enabled:false` is an explicit immutable DISABLED job spec; it consumes no
  worker attempt. Old events and historical states are not rewritten.
- Read-only job health distinguishes latest recorded results by lane/type/spec
  and lineage, with timestamps and historical counts. It is not a liveness claim.
- `phase3o_health.py` combines component, research and forward snapshots into JSON
  and Markdown with immutable private history. It runs as a fifth runner stage.
  Missing futures data remains BLOCKED; unqualified automatic challenger training
  is explicitly DISABLED. A healthy shadow core is not full platform readiness.

The existing research orchestrator ran a real nine-source archival validation
job successfully. Default unchanged futures jobs remained cached/blocked; old
index fits and evaluations were not repeated. No new market model or strategy
result was produced.

## Deterministic integration and regression evidence

An isolated `SYNTHETIC_ONLY_PROJECT` executes seven real subprocess jobs:
receipt validation → feature build → historical diagnostic and purged validation
→ training → calibrated evaluation → report. All succeed; restarting the runner
executes zero duplicate jobs. Models/results remain NO_PROMOTION, holdout scoring
is false, and no live shadow directory is touched. These fixtures are **not**
genuine backtests, forward forecasts or market performance observations.

Additional tests cover proof recovery, immutable forecasts, corrupt evidence,
same-close further revision, recent failed attempts, provider outage versus data
block, disabled/dependency-blocked jobs and the new runner stage. Existing tests
continue to cover deadlines, worker restarts, retries, isolation, duplicate
execution, source outages, holidays, DST and cashflow accounting versions.

Local verification: **348 tests passed including C++ parity**; TypeScript
typecheck passed. This branch's own CI must be inspected after push. Actual host
restart/logout and off-host failover were not performed or claimed. Starting the
existing Windows tasks is authorized local verification, not a new deployment or
security-setting change. Host still must be awake and interactively logged in.

## Futures access and quantitative readiness

All known provider keys remain absent in process/user/machine scopes. No
authenticated download, purchase or consumption attempt was made. Licensed NQ/ES
rows: **zero**. Quote USD, entitled range, credit eligibility and resolved provider
IDs remain unknown, not zero or fixture-derived. `PHASE3O_DATA_ACCESS.md` is the
concise operator checklist; the working adapter/approval workflow was not rebuilt.

No new information-qualified market experiment exists, so no additional market
training was justified. Direction, target probability and survival outputs remain
null and trading-ineligible. Cashflow-v2 and legacy-v1 stay distinct. Licensed
trades/quotes/depth, sufficient independent samples, PIT economic events and
validated order-flow/auction feature ablations remain unmet research dependencies.

Readiness and explicit pre-frontend gates: `BACKEND_READINESS.md`.
No arbitrary 70% or prediction-accuracy percentage is assigned.
