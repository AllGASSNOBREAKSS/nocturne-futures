# Phase 3Q — bounded scheduled recovery and isolated deployment proof

Base `84a4ea9`; branch `feat/phase3q`; November 6, 2026 UTC.
**Backend acceptance: NO-GO frontend. NO_PROMOTION / NO_TRADE.**
No frontend, TradingView automation, broker execution, new market-model training,
exposed-holdout tuning or paid data consumption.

## Starting evidence and preservation

Phase 3P implementation CI and its evidence-only follow-up both passed:
- `8994d9e`: run 42131793179.
- `84a4ea9`: run 42132262561.

The starting tree already contained a legitimately appended third forecast and
second outcome plus scheduler reports. These changes were preserved and audited,
not reset. Original Phase 3P forecast/outcome bytes remain unchanged prefixes;
frozen model SHA-256 remains
`515fbf7222fd81159fa017facb68c88020afd63c3e2ddec00178d65d0821434e`.
`reports/phase3q_acceptance.json` records exact prefix/hash evidence and current
counts. Historical experiment reports/weights are not recalculated or replaced.

## 3Q.1 — scheduled operation

The old exit **3221225786 / 0xC000013A** means STATUS_CONTROL_C_EXIT. Some old
runs left no completion receipt. Task Scheduler's Operational log is disabled;
available System queries show no matching recent sleep/shutdown event. The host's
last boot predates the interruptions. Neither the control-event sender nor a
particular user/logoff/scheduler policy is established. No logging/security policy
was changed to obtain evidence. See `phase3q_host_diagnostics.json`.

A hidden-window PowerShell action was **not sufficient**: three repeated launches
included one interrupted shadow run, with lifecycle evidence stopping at audit.
Its actual failure is retained in `reports/phase3q_hidden_experiment.json`.
A visible-baseline retry also happened to succeed, so no deterministic attribution
to user window closure is claimed (`phase3q_visible_baseline.json`).

Implemented a minimal console-free transport, not a replacement scheduler:
`pythonw.exe` runs `scripts/run_headless_task.py`, launching the existing PowerShell
runner with `CREATE_NO_WINDOW`. Startup/child/exit/timeout events are fsynced.
Existing runners now also append run/stage lifecycle evidence and use exclusive
wrapper guards. Overlap returns **75**, a child failure remains nonzero and launcher
timeout returns **124**; no interrupted status is remapped to success. Existing
lane locks, dependencies, retry budgets, restart recovery and worker watchdogs
continue unchanged. Parent deadlines precede scheduler hard limits.

Only the two task **Actions** were updated. XML comparison proves principals,
settings and triggers unchanged (`phase3q_task_action_changes.json`). Original
definitions are private in ignored `data/recovery/phase3q-task-definitions/`.
Installers use the same windowless transport for future approved registrations.

**Observed recovery:** three actual Task Scheduler launches per task, six complete
zero-exit runs, all with matching launcher/runner receipts; shadow stages all exit
0 and launcher records show no console window. Evidence:
`reports/phase3q_scheduler.json`. This supports the console-free mitigation under
tested host conditions; it does not prove the unknown sender can never terminate
another process. Sender/root-origin investigation remains limited by unavailable
history. Long-duration soak and reboot/logoff are not tested.

The existing automatic half-hour shadow trigger also completed at 01:17 UTC,
without a manual start, exit 0 with complete console-free launcher/stage receipts.
Its separate observation is `reports/phase3q_timed_shadow.json`.

Current tasks remain Interactive/Limited, 30-minute shadow and six-hour research.
The machine must remain awake and logged in. Logout-independent deployment needs
operator-approved account/credentials or an authorized always-on host. None was
configured or purchased; no 24/7 availability or off-host paging claim.

## 3Q.2 — fresh environment and private recovery

Created a new **no-system-site-packages venv**, independent local Git clone and
fresh C++20 native build in the approved private temporary area. Installed public
package dependencies, not paid market data. The successful source snapshot for
the final pinned environment is `001d55b`; later documentation/evidence commits do not
change the tested native/core runner implementation.

Important negative result: a broad fresh dependency resolution (NumPy 2.5.4,
pandas 3.1.1) passed **361 tests**, but failed exact replay of all three authentic
issuance proofs and both outcomes. Those files were still byte-intact. We retained
AUDIT_BLOCKED, did not loosen any checks, and did not change the model or evidence.
Pinning only NumPy/pandas back to 2.5.0/3.0.3, leaving other fresh packages unchanged,
restored all exact proofs and both fixed diagnostics. The combined intervention
does not isolate a single dependency's internal cause. See
`reports/phase3q_dependency_incident.json`.

The Windows/CPython-3.14 dependency lock and environment attestation now make that
constraint explicit. Final fresh pinned environment: **362 passed, zero skipped**,
including native parity, wrapper overlap/failure and actual windowless timeout
contracts. Package/native import locations point to the clean clone/build; user
site packages are disabled and every dependency pin matches. `pip check` passed.
An explicit runtime-constraint regression gate now rejects unreviewed dependency
drift; both Python CI jobs install the same numerical constraints.
Report: `phase3q_environment.json`.

New private snapshot: **654 files / 228,647,450 bytes**, checksum
`b3eaf5a1526f1c6e9ce61f68c179654e1f13dc26c2ea17b1db70ede613e63bf3`.
Pinned clean-venv replay verifies three forecasts, two matured outcomes, six cached
challenger files and exact reproduction of the two fixed index diagnostics.
Then a newly initialized, empty SQLite state executed one real DATA_VALIDATION
job against all **nine archived source histories**, with captured bytes reverified
afterward. No market-model fitting, new trading research or shadow issuance was
performed in the isolated copy. Reports: `phase3q_recovery_*.json` and
`phase3q_clean_validation.json`.

This is **fresh-environment recovery on the same Windows host**. It still uses the
installed OS, CPython base, MSVC/SDK and local storage. No separate machine,
clean OS, authorized off-host location, encrypted off-host archive, service-account
installation, live-state cutover or rollback was tested. The runbook
`PHASE3Q_DEPLOYMENT.md` documents prerequisites, builds, secrets, state initialization,
historical-path limitations, task installation, health checks and safe rollback.

## 3Q.3 — genuine forward evidence

Current audits: **3 issued / 2 verified matured / 1 pending / 0 missed**.
Legacy cohort: one issued/one matured; corrected residual-adjusted-v1: two
issued/one matured. Zero open operational alerts in the current core report.
Repeated scheduled cycles are idempotent: no duplicate prediction or outcome.

November 5 outcome for `3db9c4cbd3a9cc5944db8437` was appended at actual evaluation
time `2026-11-06T00:47:10.805475+00:00`, after the 00:00 UTC availability bound;
its archived source was received at `00:47:09.891512+00:00`. Canonical forecast hash
remains `86169b61e5ed6c944b0c7fc617f810740c031510b79739524a88920c52df0e57`.
Original denominator remains **28437.166015625**, not the later revised close.

- Observed high/low: 28078.185546875 / 26606.427734375.
- Realized range: **1471.7578125 points**, fraction **0.05175472871281661**.
- P50/P80/P90: **all not covered**.
- Pinball P50: `0.017448145234075434`; P80: `0.02131315690327859`;
  P90: `0.01863813408992034`.
- Immutable outcome SHA-256:
  `03883e005708913cc3281df8662a0d8e971a24cec2773107e76144acd88bd574`.

The new November 6 forecast `291aac9c9d893a888609aafd` was actually issued at
`2026-11-06T00:47:12.720972+00:00`, not backfilled; it remains pending. Its new
reference close is 26629.80859375. Earlier November 4 outcome remains unchanged.
All are **unofficial-provider research-grade**, not independently exchange-final.
Exact source/timestamp/reconciliation/forecast gates remain enforced. No aggregate
predictive accuracy, calibrated coverage or trading edge is inferred from two
observations, particularly across distinct inference cohorts.

## 3Q.4–3Q.6 — data gate and research governance

Acquisition is **USER_ACTION_REQUIRED**. Databento/FRED/BLS/Nasdaq Data Link keys
remain absent in process/user/machine scopes. GLBX.MDP3 entitlements, raw IDs,
credit eligibility, billable bytes and cost remain unverified; quoted USD is null,
not zero. Zero licensed NQ/ES rows; no authenticated or metered request attempted.
The single exact configuration/quote/approval/pilot checklist remains
`PHASE3P_DATA_ACCESS.md`; current secret-free status is `phase3q_data_access.json`.
No adapter was rebuilt and no blocked download retried. The user must configure
authorized access and approve actual per-request quotes, even for credit use.

Existing minute bars and complete 5m aggregation require authentic raw contracts;
volume-at-price/CVD needs trades, bid/ask needs quotes, and depth needs entitled
sequence-valid book data. Bar OHLCV cannot supply them. Authentic futures backtests,
new walk-forward ML, direction/consolidation/auction/200–500-point target-first
research remain **BLOCKED**, not successful zero-trade runs.

Actual independent work here: genuine nine-source validation and operational
forward evaluation; exact replay of old fixed diagnostics for recovery proof only.
NDX history spans 41.09 years; cash indices/ETFs/continuous futures proxies remain
separate, with bar-end lower-bound provenance rather than vintage-certified PIT.
The fixed index diagnostics remain negative at hypothetical 2 bp (NDX mean fraction
`-0.00016316773640181952`, S&P `-0.0003269370965258071`, 6,036 observations each).
These are not NQ/ES execution results or new discoveries. No new hypothesis or
independent eligible data justified training another challenger; previous weak
logistic/frequency findings remain unchanged. No LightGBM search or exposed-holdout
reuse. Frozen inference is isolated from research; NO_PROMOTION / NO_TRADE.

## 3Q.7 — acceptance

`BACKEND_READINESS.md` and `reports/phase3q_acceptance.json` separate engineering
evidence from quantitative validity. **NO-GO frontend; no arbitrary 70% claim.**
Bounded orchestration, local scheduling, native integration, fresh venv/private
proof replay and append-only forward evaluation have evidence. Remaining gates:
separate-host/off-host durability and cutover/rollback; approved unattended account
and long-duration/reboot/logoff testing; hard memory isolation; API deployment
authentication/security/load review; independent monitoring/paging; authorized
futures pilot and sufficient independent direction/strategy/target calibration
evidence; adequate forward outcomes per frozen cohort.

Local suite: 362 tests including native parity; pinned isolated suite: 362 tests
including freshly built native parity; TypeScript passed; installer dry runs passed
without registering extra tasks. Existing Starlette/httpx and CMake policy warnings
are not suppressed. All four Phase 3Q CI jobs passed for implementation
`001d55bebb57aa1afacc8fb5e7c04c33cb0220dc` (Python, TypeScript, native,
Windows-shadow):
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/42142381461
Machine-readable evidence is `reports/phase3q_ci.json`. Subsequent documentation/
observation commits must not be confused with that tested implementation SHA.
