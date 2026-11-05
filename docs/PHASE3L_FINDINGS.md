# Phase 3L — first verified forward observation and futures research readiness

Checkpoint: 2026-11-05 UTC (November 4 evening in New York).
Branch `feat/phase3l`, base `262c4dc`. Trading remains **NO_TRADE**.

## Starting verification and genuine scheduler output

Phase 3K reproduced **265 passing tests including native C++ parity**. Both
reported commits were verified green; latest run:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41782943095

The existing scheduler had already appended the first outcome at
`2026-11-05T00:17:10.441833+00:00`, then issued the November 5 forecast at
`00:17:12.620017+00:00`. Those uncommitted runtime records were inspected and
preserved before extending the implementation. No backfill or rewriting occurred.

Current state: **2 issued, 1 verified research-grade matured, 1 pending, 0 missed**.
The matured record is legacy unadjusted inference. Corrected residual-adjusted
inference has one issued forecast and **zero matured outcomes**. Keep cohorts
separate; this is not a validated corrected-model sample.

## First real forward evaluation

Forecast `20d48fc41c2cc0f5c0ae4f2d`, November 4 NDX cash session:

- Original denominator: **28180.263671875**, unchanged.
- High: **28829.662109375**; low: **28276.21875**.
- Actual range: **553.443359375 index points**.
- Fractional range: **0.019639396061696825**, or **1.9639396062%**.
- P50: 478.4103990943 points; **not covered**; pinball **0.0013313033751989351**.
- P80: 737.8492329340 points; **covered**; pinball **0.0013087590358005139**.
- P90: 805.0573836309 points; **covered**; pinball **0.0008928732079501124**.

Pinball units are fractions of the reference close, not dollars or trade profits.
Total daily range does not establish NQ direction or a 500-point target-first
opportunity. These are **one observation's descriptive results**, not accuracy,
calibration or trading-edge claims.

Outcome snapshot:
`2bdadb4e3d17c80a4358eed656b475e0129bfc86dfd217695a9d9659f50f7ec0`.
Raw hash:
`4b1e33c93d48d63fea2763646b66c02351c97c7a2637d6299d6e4cff8e30265c`.
Normalized hash:
`3a25e87ec507a0ab693acd1a1ad52db31190c1111f331f5cfa68024f6c84f1b1`.
Response received `2026-11-05T00:17:09.704122+00:00`. The source bar starts at
November 4 14:30 UTC; availability bound is November 5 00:00 UTC, after the
November 4 21:00 UTC cash close.

`phase3l_forward_audit.py` independently checks snapshot hashes, upstream INDEX
identity, session timestamps, OHLC completeness/consistency, receipt/evaluation
chronology, forecast seal/hash, original-denominator reconciliation, point
conversions, coverage, pinball and stored bar digest. It writes reports only.
Evidence and journal hashes: `reports/phase3l_forward_audit.json`.

The original first forecast line remains byte-identical, SHA-256
`61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3`.
The outcome's canonical forecast hash is
`26604fd0603ca5f5e6dac216797fe24b96143e4abc63ceeae597a32b7290d3e2`;
these are different serialization conventions, not a discrepancy.

Classification is **VERIFIED_RESEARCH_GRADE**, not independently certified
exchange finality or minute-by-minute coverage verification. Yahoo is unofficial
and revisable. Evaluation stays linked to the source observed at evaluation,
never silently re-scored on later prices. The November 3 revision remains
separately reconciled as issued.

## Frozen baseline and verified reporting

The train-only comparator was committed in `92cd098` at November 4 04:51 UTC,
before the outcome but **after issuance**. It was not embedded in the first
forecast. The comparison is explicitly labeled
`POST_ISSUANCE_FROZEN_TRAIN_ONLY_COMPARATOR_NOT_AN_ISSUED_FORECAST`:

- P50 baseline pinball: **0.0026809509185644707**.
- P80 baseline pinball: **0.0009371283706551635**.
- P90 baseline pinball: **0.0013281705419723002**.

No baseline field was inserted into either journal. Future corrected forecasts
already carry their comparator at issuance. The standard report now includes
independent outcome verification, cohort counts and comparator registration.
Rejected/duplicate outcomes are quarantined, not counted as performance or repaired.
The 30/60/90 milestones remain future monitoring counts, not promotion promises.

`GET /v1/shadow/verification` exposes the timestamped audit report, not a fresh
exchange-finality certification on each request. Archives remain local/private;
a clone alone cannot rerun verification without authorized archive transfer.

## Authentic futures access

Databento, FRED, BLS and Nasdaq Data Link keys are absent in process, Windows user
and machine environments. No values were printed; no licensed request, purchase
or entitlement claim was made. NQZ6 and ESZ6 inventories both have **zero rows
and zero verified receipts**. Details: `reports/phase3l_readiness.json`.

- Pilot: `GLBX.MDP3`, `raw_symbol`, `ohlcv-1m`, NQZ6/ESZ6, November 1 23:00 UTC
  through November 2 22:00 UTC. At most 2,760 minute rows under the planning
  assumptions; this pilot was **not downloaded**.
- Plumbing needs one full session per contract. Predictive research should seek
  3+ years across contracts/regimes plus adequate independent event counts and
  separate chronological training/calibration/holdout. Years alone prove nothing.
- Storage assumptions remain approximately 104–174 MB of annual NQ/ES 1m CSV
  plus 21–35 MB of derived 5m CSV; calendars, roll overlap and encoding change it.
- **Cost is null, not zero.** Exact provider size/cost depends on authenticated
  dataset/schema/date bounds and exchange entitlement. No defensible quote is
  available without access; public documentation access also failed. No purchase
  is authorized by the planning estimate.
- Trades, quotes, volume-at-price, CVD, DOM/depth/MBO and actual VX remain blocked.
  Configure credentials locally, never in chat; see `FUTURES_DATA_REQUIREMENTS.md`.

## Functioning receipt replay, without fake research data

`research/contract_replay.py` verifies the existing private receipt layout:
request/schema/license, raw/export hashes, raw-to-normalized equivalence, contract
identity, ticks, OHLCV and overlaps. It reuses existing aggregation and target
labeling. Invalid OHLCV and duplicate times are rejected. Equal timestamps with
different datetime resolution no longer disappear from complete 5m aggregation.

Session context uses only completed bars available asof. It reports measured
high/low/close and an explicitly labeled **bar VWAP proxy**. True VWAP, POC/VAH/
VAL/HVN/LVN, CVD and book imbalance stay null without appropriate authentic data.
Existing profile/order-flow implementations were not rebuilt.

Bar-end availability is a **lower bound**, not proven historical dissemination
or vintage history. Replay is receipt-verified research only. Provider-authoritative
calendar/roll review and availability evidence are required before promotion.

The NQ grid supports 50/100/200/350/500-point candidates over 12/24/72 five-minute
bars using existing barriers and costs. Candidate-entry and actual-fill distances
are distinct. All targets/horizons from one setup share a group; rows are not
independent trades. Intrabar ambiguity and censoring remain explicit. Unsupported
external features are excluded; strategy/regime tags remain uncertified. Target
probabilities are null and promotion remains `NO_PROMOTION`.
ATR normalization reuses the existing calculation on completed same-contract
bars available asof; unavailable ATR stays missing, and supplied future ATR is
never accepted as evidence.

`phase3l_contract_replay.py` returned `DATA_BLOCKED` and **zero target rows** on
the actual empty inventory. Tests use isolated fixtures, never live journals.

## Statistical corrections, not a newly fitted survival model

AJ-v1 incorrectly reduced survival on censoring. AJ-v2 updates survival by event
hazards only; censoring affects later risk sets. Analytic case “one censor at
bar 1, one target at bar 2” now gives target incidence 1 rather than 0.5. This is
a mathematical test, not a market probability. Non-informative censoring and no
hazard extrapolation beyond observed support remain assumptions.

Target rows now retain their observed contiguous prefix. Truncated censoring
uses observation end, not intended full horizon. Legacy rows missing observation
end get unknown duration and must be excluded, not invented. Fractional event
codes/bar counts and invalid horizons are rejected. ATR enrichment now computes
on the available subset, preventing late-published past bars from leaking through
an index-count shortcut. Version: `aj-discrete-v2-event-only-survival`.

Old AJ-v1 reports remain preserved historical outputs, **not current evidence**;
recompute and review before reuse. Other Phase 3F composition remains unaudited.
No authentic-data survival fit, frequency/logistic/LightGBM comparison or new
directional ablation was possible.

Hypotheses awaiting data include aggressor imbalance conditional on activity,
trade-derived value migration beyond OHLCV state, and session-conditioned NQ/ES
relative response. Require leakage-safe availability/provenance, grouped purged
chronological evaluation and baseline improvement. New AUC, balanced accuracy,
recall, Brier and calibration are **null**, not inferred from architecture. Session
predictions remain unpromoted and separate from measured current state.

## Public context, C++ and operations

Bounded official probes now succeed without weakening TLS/network security:
FRED returned 24 DGS10 rows and BLS 21 CPI rows. FRED NASDAQ100 returned November 3
only, not November 4 corroboration. It is a separate distributor with shared
Nasdaq origin, not independent high/low confirmation. Current-vintage observation
dates are not release timestamps or consensus; historical PIT eligibility stays
false. ALFRED credentials, authorized event schedules/news and consensus history
remain missing. Event risk never becomes price bias.

The unchanged C++ aggregation kernel was benchmarked on 100,000 explicitly
synthetic performance inputs, five repeats: Python median ~0.01743 s, native
including conversion ~0.00291 s, measured ratio ~5.99x, exact parity. This is
host-specific kernel timing, not end-to-end replay speed or predictive evidence.

Local verification: **291 passed including C++ parity**. TypeScript and task
definition checks are verified locally/through this branch's CI; do not substitute
Phase 3K CI. Diagram/source: `ARCHITECTURE_PHASE3L.md`, `architecture_phase3l.png`.
Only NDX range remains shadow-active; no orders are enabled.

The interactive task still needs a logged-in user and awake host. Unattended
installation requires an authorized account credential and OS rights. No principal,
credential or privilege was changed; local monitoring is not off-host paging.
The runner now refreshes the independent audit before the standard report and
monitor. Missing, stale, failed or journal-mismatched verification produces a
durable operational alert rather than silently treating old results as current.
One wrapper run during concurrent testing returned failure with empty child
audit/report output; its underlying process failure reason was not established.
The runner now invokes Python directly and records each stage's actual exit
code, avoiding detached-process handle ambiguity. A subsequent real four-stage
run returned zero for cycle, audit, report and monitor. Windows tests separately
exercise harmless stderr and forced failure/continuation in isolated scripts.
No old logs were erased and no uptime guarantee follows from those checks.

Next: obtain GLBX.MDP3 entitlement and an exact authorized pilot cost quote, ingest
the two bounded contracts, validate calendar/roll/availability evidence, then expand
history and test genuine new feature information. Meanwhile let the November 5
forecast mature after the November 6 00:00 UTC adapter bound. Do not retrain the
frozen range model or infer accuracy from this single legacy observation.
