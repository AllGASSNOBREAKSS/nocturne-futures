# Phase 3I — forward operation and data reliability

Engineering checkpoint: 2026-11-04 UTC. Branch `feat/phase3i`, base `e963981`.
Trading remains **NO_TRADE**. This checkpoint is not completion of forward
validation or a claim of continuous service availability.

## Observed forward state

- Issued: **1**, matured: **0**, awaiting outcome: **1**, missed: **0**.
- Original forecast: `20d48fc41c2cc0f5c0ae4f2d`, issued
  `2026-11-04T02:53:30.237804+00:00`, target `2026-11-04`.
- Journal is byte-identical to `e963981`. SHA-256:
  `61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3`.
- Original feature digest:
  `edea8e109ab6f627759d0cb27fc407a3770c1557bf8e949dd5b31c6df19cb365`.
- A real Yahoo refresh returned NDX/VIX data through November 3 only. The
  November 4 outcome is not available; no outcome record was manufactured.
- Reference close is 28,180.263671875. Range fractions multiply this close to
  obtain index points; multiplying by 100 gives percent. These are total cash
  session ranges, not directional excursions, high/low destinations or NQ targets.

## Calibration defect found and corrected

Phase 3H runtime omitted the residual adjustments already frozen in metadata.
The historical evaluation included them. `ShadowArtifact.predict` now applies
those adjustments before nonnegative clipping and monotone sorting. No fitting,
recalibration or tuning occurred; `model.joblib` and `metadata.json` are unchanged.

New forecasts record `inference_revision=residual-adjusted-v1` and calibration
status. The first forecast remains unmodified and is reported as
`legacy-unadjusted`. Its eventual outcome will be scored against its **issued**
quantiles, never corrected retroactively. Aggregate descriptive metrics are
accompanied by inference-revision groups; the legacy forecast is not evidence of
the corrected inference path's calibration.

`phase3i_audit_artifact.py` verified actual runtime inference across the already
used 712-row holdout: coverage 0.5337078652 / 0.8160112360 / 0.9199438202;
pinball 0.00219592158 / 0.00193771179 / 0.00140948189. This is diagnostic parity,
not another independent test. Do not tune against this holdout.

`baseline.json` separately freezes empirical quantiles from the original 9,134
training rows only. Generation embeds this comparator in future forecasts.
The legacy forecast has no pre-issued baseline and its comparison remains null.

## Storage, recovery and failure controls

- Host-local OS advisory locks replace age-based lock-file deletion. An active
  lock cannot be stolen after a timeout; process death releases it automatically.
- Serialized store mutations enforce one issuance per model/instrument/horizon/
  target date, including when revised input data would produce a different ID.
- Retries retain original forecast timestamps. Outcome retries retain original
  evaluation timestamps; conflicting realized values are rejected.
- Journal writes flush and fsync. Partial/corrupt records fail closed and require
  supervised recovery; code never truncates or silently repairs originals.
- Missed issuance is recorded after the opening deadline, using the calendar,
  even without provider bars. Recovery scans from service activation, including
  outages longer than 30 days. It never constructs retrospective forecasts.
- Operational refreshes verify symbol, frequency, receipt age (36 hours), raw
  and normalized hashes and OHLC completeness. No fallback to frozen research
  files is allowed for new operational forecasts or evaluations.
- Yahoo retries remain bounded by the existing adapter. Structured JSONL logs,
  quality incidents, atomic status-file replacement and health exit codes expose
  failures. Successful-cycle timestamps, not arbitrary log writes, drive health.
- One quality incident remains recorded from a freshness-check defect discovered
  during implementation: cycle time was captured before network receipts. This
  was fixed by advancing the wall-clock after refresh; history is not erased.

Outcome evaluation separately requires a valid completed cash bar, a publication
availability bound after session close, finite consistent OHLC, a pre-open
forecast, and an integrity audit. Outcomes include point/fraction units, source
availability, bar digest and inference revision. The adapter's next-UTC-midnight
availability is a conservative bound, **not an observed exchange publication
timestamp**. Official exchange finality and independent cross-source verification
remain stronger future requirements; Yahoo is an unofficial research source.

The bounded cash-equity calendar supports 2025–2027, DST and explicit early
closes, and refuses unsupported years. It is distinct from futures calendars.
Future emergency closures still require calendar maintenance; no authoritative
calendar feed or production SLA is claimed.

## Windows deployment

`install_shadow_task.ps1` installs `Nocturne-NDX-ReadOnly-Shadow` for the current
user: every 30 minutes and at logon, no overlapping instances, retry on failure,
start-when-available and a 20-minute execution limit. `run_shadow_task.ps1` runs
the existing service with refresh and then the forward report. No credentials
are embedded. Installation was performed on this host; inspect Task Scheduler
for current runtime state rather than assuming perpetual availability.

A real scheduled cycle completed at 2026-11-04 04:47 UTC with task exit code 0,
fresh NDX/VIX receipts and `ALREADY_ISSUED`, leaving the original forecast intact.

This is an **interactive-user** task: the host must be awake and the user logged
in. Logout-independent operation requires a separately authorized service
account, Python environment and credential/network setup. OS task persistence is
not proof of future execution. `--loop` is still available and Ctrl+C releases
the cycle lock; Task Scheduler owns persistent restart behavior here.

```powershell
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3i_forward_report.py
python scripts/phase3h_shadow.py --health
Get-ScheduledTask -TaskName Nocturne-NDX-ReadOnly-Shadow | Get-ScheduledTaskInfo
# For another host (refuses to overwrite an existing task):
powershell -NoProfile -File scripts/install_shadow_task.ps1 -WhatIf
```

## Monitoring and read-only APIs

`phase3i_forward_report.py` produces JSON and Markdown at zero or few outcomes.
It reports integrity, issuance/maturity/missed counts, quality incidents, health,
30/60/90 monitoring milestones, monthly/regime coverage, descriptive drift,
pinball and available train-only baseline comparisons. Wilson coverage intervals
are nominal Bernoulli intervals, not dependence-adjusted confidence guarantees.
With zero outcomes there are no forward coverage or pinball numbers.

Added endpoints: `/v1/shadow/missed`, `/v1/shadow/calibration`,
`/v1/data/futures-readiness`, `/v1/alerts/critical-day`. Existing endpoints remain
compatible. Reports are timestamped snapshots, not proof of live connectivity.
The calendar alert defaults to `DATA_BLOCKED`; a schedule-proximity module
requires explicit authorized PIT coverage before declaring absence of event
risk. It returns no directional bias and does not expose unreleased actuals.

## Futures research and remaining dependencies

Credentials checked without revealing values: Databento, FRED and BLS keys are
absent. Databento connectivity/entitlement is **not tested** and no billable
request was made. `phase3i_readiness.py` reports the existing public context
inventory separately from three blocked futures tiers. Exact entitlement and
bounded ingestion commands remain in `FUTURES_DATA_REQUIREMENTS.md`.

`research/contract_targets.py` prepares 1m/5m contract-specific target datasets.
It validates quarterly NQ/ES raw symbols, identity, ticks, OHLC, volume,
availability and duplicates. Candidate rows retain setup/session/regime,
cost assumptions, market-open entry semantics, ATR distance when provided,
full-horizon MFE/MAE, touch versus target-first, competing stop/timeout events,
event-time upper bounds and ambiguity/censoring. Signal groups include contract
identity. Gaps censor outcomes; simultaneous barriers remain ambiguous.
Passing structural validation alone never establishes authentic provenance.

Tests use synthetic fixtures outside the live journals. No genuine contract
dataset, order-flow feature ablation or new survival model was trained. POC,
VAH/VAL, VWAP and order-flow context can be supplied as separately PIT-verified
setup features; OHLCV cannot establish authentic footprint or depth. Existing
Phase 3F hierarchical/Aalen–Johansen methods require a separate statistical
audit before reuse; this wrapper only reuses barrier labeling, not those fitted
probabilities. No direction, strategy or target model is promoted.

Authorized PIT calendars/news/consensus, licensed trades/quotes/depth/MBO and VX
remain blocked. More model families on unchanged features are not justified.

## Verification and next milestone

Local suite: **241 passed**, including native C++ parity. Task installer dry run
passed. Base `e963981` GitHub Actions was independently verified successful.
Phase 3I commit/remote CI status is recorded in the implementation checkpoint;
do not infer it from the base run.
CI now also tests Windows shadow operations and the task-definition dry run;
CI never registers an actual task.

Next: verify the installed task's real exit state, then evaluate the first
forecast only when its completed November 4 bar is available (adapter bound
November 5 00:00 UTC). Accumulate real corrected-inference forecasts and report
their separate sample counts; 30/60/90 are monitoring milestones, not promotion
guarantees. Obtain Databento entitlement before contract-level empirical research.
