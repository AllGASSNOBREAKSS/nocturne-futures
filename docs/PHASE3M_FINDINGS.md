# Phase 3M — durable research orchestration

Checkpoint: 2026-11-05 UTC. Branch `feat/phase3m`, base `6c04c50`.
**NO_PROMOTION / NO_TRADE. No frontend or execution changes.**

## Verified baseline

Phase 3L reproduced **291 passing tests with native parity**. Its CI run was
independently checked successful:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41950036267

Scheduler-updated reports were present on entry and were retained, not reset.
All forecast bytes still equal the Phase 3L version; the original first-line
hash remains `61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3`.
Frozen model weights were not trained, replaced or promoted.

## Working job runner, not just interfaces

All twelve requested types have actual bounded handlers:
`DATA_REFRESH`, `DATA_VALIDATION`, `FEATURE_BUILD`, `HISTORICAL_BACKTEST`,
`WALK_FORWARD_VALIDATION`, `MODEL_TRAINING`, `MODEL_EVALUATION`,
`SHADOW_FORECAST`, `FORECAST_MATURITY_CHECK`, `FORWARD_EVALUATION`,
`MODEL_DRIFT_MONITOR`, `RESEARCH_REPORT`.

`research/orchestrator.py` owns persistent SQLite state, same-lane dependencies,
immutable idempotency specifications, attempts, backoff, terminal statuses,
process timeouts and restart recovery. OS locks distinguish a dead runner from
a still-running orphan; workers also have a watchdog. Reserved/partial attempts
are never silently overwritten. Logs and transition histories survive retries.
Independent report jobs still run when a data/training dependency fails.

Shadow and research lanes have separate processes and locks. Training is rejected
from the shadow lane; cross-lane dependencies are rejected. Numerical threads are
limited to one, research priority is lower, and default work is 20 jobs/900s plus
an independent report up to 60s. Hard memory quotas, multi-host failover and
off-host monitoring are **not implemented**. See `ARCHITECTURE_PHASE3M.md`.

The first validation attempt found a real legacy-schema difference: original
normalized receipts predate `source_complete`. The verifier was corrected to
compare their actual archived columns and derive completeness from the verified
raw quote arrays, rather than assuming imputed bars were complete. Retry succeeded;
the original failure and attempts remain in SQLite and exported event history.

## Actual historical work

Nine daily source receipts passed raw/normalized checksum, identity, reconstruction,
value and chronology checks. Coverage includes NDX **10,353 rows / 41.09 years**,
S&P 500 **24,828 rows**, VIX **9,280**, TNX **16,198**, QQQ **6,956**, SPY **8,498**,
TLT **6,105**, NQ continuous proxy **6,573**, ES proxy **6,587**. Instruments and
source classes remain distinct. Coverage is not a claim of independent PIT history.

Two versioned index-context datasets contain **6,036 development observations
each**, 2000–2023. Availability is prior completed-bar lower-bound evidence;
current-vintage histories do not reconstruct actual historical dissemination.

Two fixed prior-20-session sign backtests were executed on those datasets, entering
the next observed open and marking at its close. They have 0/2/5-bp hypothetical
cost sensitivity, average gains/losses, expectancy, profit factor, compounded
drawdown and year-by-year results. At 2 bp, mean unit returns are approximately
**-0.00016317 NDX** and **-0.00032694 S&P 500**, with profit factors **0.96774**
and **0.91690**. These negative retrospective diagnostics are preserved; nothing
was tuned to improve them.

These are explicitly **non-executable index context**, not NQ/ES dollar P&L or
licensed-contract strategy backtests. Stop-first/target-first/MFE/MAE are null,
not manufactured from a missing intraday path. The authentic-futures strategy
job returned **BLOCKED: AUTHENTIC_CONTRACT_HISTORY_REQUIRED**. No actual ORB/VWAP/
value-area licensed-contract result is claimed. Broader regime/session strategy
automation remains incomplete pending data; existing engines were not rewritten.

## Actual controlled ML diagnostics

Two fixed logistic challengers were trained, each with **three purged development
folds**, separate 250-group calibration and 250-group test blocks, five-day
embargo and fixed seed/C. Each has **750 development test predictions**.
Features are trailing 1/5/20-session returns, trailing volatility and range
fraction, not invented order flow. Label is next observed session close above
its open, not next-day close-to-close or NQ target-first.

- NDX: model Brier **0.249911**, frequency **0.249863**, AUC **0.47136**, balanced
  accuracy **0.50094**. Reject an incremental-performance claim.
- S&P 500: model Brier **0.248798**, frequency **0.249196**, AUC **0.54045**,
  balanced accuracy **0.51819**. A small development difference, not independent
  evidence of a tradable or calibrated directional advantage.

Class recall, reliability bins, ECE, fold boundaries, model/data/source checksums
and environment versions are stored. No hyperparameter search, new LightGBM fit,
neural model, neutral-class model or new survival fit was justified or claimed.
The 2024+ region is excluded from these new jobs; it was previously used by other
research and is **not rebranded as an untouched holdout**. Earlier periods also
have prior research exposure and are development diagnostics only.

Identical dataset/protocol/code/sklearn identities reuse saved training and
evaluation, rather than repeated fitting/scoring. Incomplete artifacts block for
operator review; model/prediction corruption blocks reuse. Original training code
was saved after verifying it still matched each recorded pre-fit code hash; no
forecast or model result was regenerated to add that code archive. Unit tests
independently demonstrate deterministic fits on fixtures. Private experiment and
attempt history is not included in Git; backup is a deployment requirement.

## Forward state and scheduling

The orchestrator executed real refresh, shadow, maturity, independent audit and
monitor/report adapters. They reuse the existing locked/idempotent services; a
successful job does **not** mean a forecast was newly issued or an outcome matured.

Current state remains **2 issued / 1 verified matured / 1 pending / 0 missed**.
The first observation is legacy inference, 553.443359375 index points, P50 not
covered, P80/P90 covered. Corrected inference still has **zero matured outcomes**.
November 5 is not complete; earliest adapter evaluation bound is November 6
00:00 UTC. There was no backdated forecast or fabricated future observation.

`Nocturne-ReadOnly-Research` is installed at six-hour cadence plus logon, interactive
current-user/limited privilege, with 18-minute execution limit. Actual scheduled
executions completed with exit code 0. The original 30-minute
`Nocturne-NDX-ReadOnly-Shadow` task is unchanged and had a successful inspected
last run. The orchestrator shadow lane was exercised manually, not installed as
a duplicate inference scheduler. A sleeping/offline or logged-out host cannot
provide always-on coverage; unattended authorization remains separate.

## Reports, API and readiness

`reports/phase3m_research.{json,md}` combines job history, source coverage, model
metrics, failures, governance, credential presence and a separately labeled
forward-audit snapshot. Immutable historical reports/logs remain in private
attempt directories; SQLite preserves transitions rather than overwriting them.
`reports/phase3m_jobs.json` is the latest job-state view. API GET
`/v1/research/status` reports timestamp/age and marks stale snapshots; it cannot
launch work. Report snapshots omit their own in-progress job to avoid a permanent
misleading RUNNING label. No frontend was added.

`BACKEND_READINESS.md` assesses all fourteen requested categories using code,
named verifications and missing evidence. It separates implemented engineering,
bounded development diagnostics and predictive validation. No arbitrary 70%
completion figure or claim that all predictive acceptance criteria are met is made.

Databento/FRED/BLS/Nasdaq Data Link keys remain absent in all checked scopes.
`DATA_ACQUISITION_PHASE3M.md` contains the exact raw-contract pilot, entitlement,
estimated row/storage assumptions, authorization boundary and validation commands.
Cost is unknown/null. No paid download or subscription occurred. Historical PIT
macro/news/consensus and genuine trades/quotes/depth remain unavailable.

## Verification and next milestone

Local suite: **311 passed including native parity**; TypeScript typecheck passed.
Windows CI additionally exercises new runner/ML contracts and a research-task
definition dry run. Check this branch's own CI after push; old green CI is not
substituted for Phase 3M results.

Next: authorized GLBX.MDP3 quote/entitlement and bounded NQZ6/ESZ6 pilot, then
availability/session/roll validation and enough authentic development history
for the existing session strategies and new feature-family ablation. Meanwhile
accumulate genuine corrected-inference range observations without retraining.
Unattended credentials, hard resource quotas, private backup/off-host monitoring
and clean-host recovery verification remain engineering deployment work.
