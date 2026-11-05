# Phase 3P — reproducible private-evidence recovery

Base `ce76bf6`, branch `feat/phase3p`; checkpoint November 5, 2026 UTC.
**Partial phase delivery; externally blocked quantitative milestones remain open.**
No frontend, broker execution, paid data, new model fitting or promotion.

## Verification and forward testing

Phase 3O CI run 42126595254 was independently queried and is successful at
`ce76bf6b9144c67da11f1d0862072d023c9582ac`. Pre-existing scheduler report changes
were retained. Current local suite: **355 passed including native parity**;
TypeScript `npm run typecheck` passed. One existing Starlette/httpx deprecation
warning remains. Phase 3P implementation commit
`8994d9e331cd0bf10157b52f64cb1cc8983668cd` passed all four CI jobs (Python,
TypeScript, native and Windows-shadow):
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/42131793179
This does not certify the local Windows scheduled host; the automatic 23:47 UTC
shadow trigger also returned 0xC000013A.

Before the November 6 00:00 UTC adapter availability bound: **two issued, one
verified matured legacy-unadjusted, one pending residual-adjusted-v1**, zero
corrected-inference matured. Both forecasts pass source audits. November 5 is
not forcibly evaluated early; independent exchange finality is not established.
The November 4 observed range remains 553.443359375 points / 0.019639396061696825
of its original denominator; P50 missed, P80/P90 covered. These are descriptive
observations, not accuracy/calibration evidence. Archived observations and
reconciliation remain immutable; any new revision must pass original gates.

`scripts/phase3p_evidence.py` compares forecast journal, outcome journal and frozen
model bytes against the full Phase 3O baseline and collects current counts without
network/training. Its timestamped output is `reports/phase3p_evidence.json`.

## Implemented missing recovery verification

Added bounded local snapshot, offline relocation and exact fixed-diagnostic
reproduction in `src/nocturne/research/recovery.py`, exposed by
`scripts/phase3p_recovery.py`. It captures existing private snapshots/raw source
bodies, journals, frozen model, history receipts, research artifacts/SQLite and
licensed evidence directories. Git alone does not contain this private state.

- Cooperating research/shadow/archive/store locks are acquired non-blocking; a
  busy writer aborts capture rather than being stopped. Capture is refused within
  30 minutes before supported cash-session open. Default budget: 1 GiB/30 seconds.
- SQLite online backup includes committed WAL state; restored logical jobs/events
  and `integrity_check` are verified. Database sidecars/locks are not copied.
- Manifest binds file sizes, SHA-256, logical SQLite contents and verifier version.
  Unsafe paths, linked captured files, corruption, duplicate/unmanifested files
  and wrong verifier versions block verification. Existing destinations are never
  overwritten. Failed partial captures are retained, not auto-repaired/deleted.
- Offline audit replays original forecast/outcome checks, validates feature and
  challenger model hashes, and reproduces fixed index diagnostics exactly. It does
  not issue forecasts, load challenger pickles, train models or activate services.
- Seven synthetic tests cover relocation with original paths made unavailable,
  committed WAL, busy/deadline gates, budgets, corruption, path escape, manifest
  scope/version and byte preservation. Fixtures are not market performance.

Real v2 drill: **547 files / 210,599,711 bytes**. Manifest SHA-256:
`98daa0f8b2b7a018fd5e6425e2ea389576d9649071a9b37d1dce82191869ff86`.
Snapshot: ignored `data/recovery/phase3p-local-20261105-v2`; restored separately to
`C:/Users/huzai/AppData/Local/Temp/opencode/nocturne-phase3p-restored-20261105-v2`.
Both forecast audits and the one matured outcome verify there. Six previously
saved challenger files retain their hashes. Reports: `phase3p_recovery_*.json`.

This is **same-host relocation using the installed environment**, not off-host
durability, clean-machine dependency installation or scheduled service recovery.
It is not encrypted or uploaded; operator-managed private retention/off-host
protection remains required. Keep manual acquisition/reconciliation and other
non-cooperating writers quiescent during capture. Hashes are not signatures or
protection against a malicious local operator. No automatic backup schedule was
added. The temporary restored copy is a drill artifact, not durable backup.

## Authentic-data work, not repeated model selection

Existing research lane executed one genuine archival DATA_VALIDATION job and its
report path without fitting challengers or enabling `--index-diagnostics`.
Nine separate source histories remain distinguished as cash indices, rate/VIX
indices, ETFs and continuous futures proxies, with raw/normalized receipts.
NDX spans 41.09 years; retrospective bars are not release-vintage-certified PIT.

Recovery deliberately reproduced two **already fixed** index-context reports from
relocated authentic datasets, 6,036 observations each (2000–2023):
- NDX net mean fraction at hypothetical 2 bp: `-0.00016316773640181952`.
- S&P 500: `-0.0003269370965258071`.

These are reproducibility checks, not new strategy discoveries, independent tests
or executable NQ/ES P&L. No newly ingested licensed futures backtest exists.
Prior logistic/frequency results remain development-only, 750 observations each;
NDX Brier 0.249911 vs 0.249863 baseline, S&P 0.248798 vs 0.249196. Small differences
do not justify promotion. No LightGBM search, exposed-holdout reuse, seasonality
search or invented direction/consolidation/target probability was performed.

Price-destination research remains `research_only / NO_TRADE`: insufficient
authentic contract observations for directional excursions, realistic target-first
costs, MFE/MAE, time-to-target, acceptance/rejection or order-flow validation.
A large NDX range is not evidence of a profitable 100–500 point NQ trade.

## Operations: core reports do not prove scheduler success

Direct invocation of the existing five-stage shadow runner completes with exit
0; core audit/monitor reports are healthy. However Task Scheduler observations
and repeated explicit launches returned **3221225786 / 0xC000013A** for both tasks,
an interrupted-process status; some attempts leave no stages receipt. Root cause
is unconfirmed. Latest observation is in `reports/phase3p_scheduler.json`.
Thus scheduled operation is **DEGRADED**, not healthy merely because component
reports are green. Earlier successful 3O runs are historical, not current proof.
No tasks were deleted, reinstalled or reconfigured; principals/security unchanged.
Existing 30-minute shadow/six-hour research schedules remain enabled/interactive.
No asleep/offline/logged-out or 24/7 capability is claimed. Operator investigation
of task/host termination and a complete scheduled stages receipt are outstanding.

## Acquisition and readiness decision

`PHASE3P_DATA_ACCESS.md` is the single current acquisition decision. All four keys
remain absent across process/user/machine scopes. Existing Databento free preflight
returns DATA_BLOCKED, unknown price, no consumption. User-configured GLBX.MDP3
access, actual entitlement/raw-ID/credit verification, exact quote and explicit
approval must precede a pilot. Authentic licensed rows remain zero.

Engineering advanced only in bounded recoverability/reproducibility. Quantitative
readiness did not advance. **Pre-frontend gate NOT PASSED**; no percentage assigned.
Missing: authentic pilot and independent futures sample/event/calibration evidence,
sufficient genuine corrected forward outcomes, reliable scheduled completion,
clean-host/off-host restore, authorized availability/monitoring strategy, process
memory isolation and deployment API authentication/security/load review.

## Resume commands

After the genuine maturity bound, run the existing refresh/evaluation cycle and
audits; never backdate or automatically reconcile a changed source:

```powershell
python scripts/phase3h_shadow.py --once --refresh
python scripts/phase3l_forward_audit.py
python scripts/phase3i_forward_report.py
python scripts/phase3j_operations.py
python scripts/phase3o_health.py
python scripts/phase3p_evidence.py
```

Recovery commands require **new destinations**; example future drill:

```powershell
python scripts/phase3p_recovery.py snapshot --destination data/recovery/<new-private-snapshot>
python scripts/phase3p_recovery.py check --snapshot data/recovery/<new-private-snapshot> --restore-to <new-separate-private-location>
```

Use reviewed matching code and a trusted locally protected manifest. Do not
activate restored services against old absolute paths; this tool only maps reads
for offline proof checks. Recheck actual time, scheduled exits and source revisions
at every resume. Preserve scheduler-generated changes and all incident history.
