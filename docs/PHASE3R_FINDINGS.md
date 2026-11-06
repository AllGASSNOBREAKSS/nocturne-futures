# Phase 3R — reproducibility protection and research assurance

Base `c65e596`, branch `feat/phase3r`; November 6, 2026 UTC.
**NO-GO frontend. NO_PROMOTION / NO_TRADE.** No frontend, TradingView automation,
broker execution, new market-model fitting or paid market-data consumption.

## Verification and immutable scope

Starting tree was clean. The final 3Q commit `c65e596` was independently confirmed
CI-successful in run 42142986495. Existing reports, task definitions, frozen model,
source archives and original forecasts/outcomes were preserved. Exact baseline
journal prefixes and frozen binary hash are recorded by `phase3r_acceptance.py`.
Model SHA-256 remains
`515fbf7222fd81159fa017facb68c88020afd63c3e2ddec00178d65d0821434e`.

## 3R.1 — exact dependency and numerical protection

- Added a target-specific, complete **55-wheel hash lock** for runtime/dev/build
  dependencies: 141,178,373 downloaded bytes, actual exact PyPI SHA-256/size checks,
  then offline `--require-hashes` installation. Old 3Q locks are not rewritten.
- Installed RECORD audit verifies **13,290 hashed files** in the isolated venv,
  with prefix/version checks, corruption/path/duplicate/missing-wheel rejection.
  Trust limitations (local metadata, unhashed bytecode/RECORD, unsigned tooling)
  are explicit; this is not malware scanning or malicious-operator protection.
- Frozen inference replays all three issued feature rows, with exact float-hex
  comparison and separate legacy/corrected handling. Model loading now rejects
  drift in the six approved numerical/ML libraries before deserializing/inferencing
  the artifact. One-ULP drift and unknown cohorts fail tests.
- Runtime manifests record full Python/package versions, source commit/cleanliness,
  artifact digests, native binary hash and compiler/build flags. New Windows 3.14
  CI bootstraps only reviewed wheel bytes and runs inference/integrity contracts.
- Proposed dependency upgrades require isolated candidate review and unchanged
  original-source/golden-output checks. No new upgrade was approved and the known
  3Q rejected candidate was not pointlessly retried. No original expected values
  were regenerated to conceal drift.

Implementation: `src/nocturne/runtime_integrity.py`, existing model loader, lock/
verify/bootstrap scripts. Evidence: `phase3r_dependency_lock.json`,
`phase3r_runtime.json`, `tests/test_environment_integrity.py`.

## 3R.2 — deployment/recovery

An independent local clone and new venv installed all packages offline from the
reviewed wheelhouse with pinned build tooling and no isolated-build downloads.
The existing C++20 extension compiled freshly with MSVC, and native/package origins
were checked. No service or scheduled task was installed in the restored copy.
The private-evidence drill is still on the **same Windows host**, not separate-host
private recovery. Hosted Windows CI separately proves public-code hash-locked
bootstrap and frozen inference on its runner; no private archives were uploaded.

New coherent private snapshot: **688 files / 231,067,330 bytes**. Matching clean
runtime replay verified all three forecasts, two matured outcomes, six cached
challenger files and both fixed index diagnostics; archive/SQLite bytes reverify.
Local restore/replay elapsed **13.70 seconds**, not an end-to-end hosting RTO.
Reports: `phase3r_recovery_snapshot.json`, `phase3r_recovery_check.json`.

Proposed RPO 30 minutes / RTO 60 minutes remain unapproved/unverified off-host
objectives. No authorized independent private-evidence restore host, encrypted destination or key
custodian was provided; no upload/encryption/credential claim is made. The new
`PHASE3R_REPRODUCIBILITY.md` supplies exact bootstrap commands, upgrade gates,
recovery limits and objectives, alongside the existing 3Q cutover/rollback runbook.

## 3R.3 — genuine research assurance, not repeated model selection

The existing orchestrator executed **five genuine shadow-lane jobs**:
DATA_REFRESH, SHADOW_FORECAST, FORECAST_MATURITY_CHECK, FORWARD_EVALUATION and
MODEL_DRIFT_MONITOR. Both lane reporting paths completed. Research tick executed
zero new jobs because identical eligible daily validation was already complete;
content/idempotency caching was respected rather than inventing new work.

`reports/phase3r_assurance.json` inventories all 12 supported job types, separates
prior persisted evidence from work updated in this phase, and retains blocked
raw-futures jobs. Previously genuine nine-source validation, two 6,036-observation
cash-index diagnostics and saved logistic development experiments remain evidence,
not new independent results. There was no new information-qualified feature,
backtest, walk-forward training or model comparison to justify another fit.

The private restore deliberately replayed the two already-fixed index diagnostics
for reproducibility only. Both remain negative after hypothetical 2 bp: NDX mean
fraction `-0.00016316773640181952`, S&P `-0.0003269370965258071`. They are not
execution-grade NQ/ES P&L. No final holdout reuse, parameter search or automatic
challenger promotion occurred. Long-term cash indices, ETFs and continuous proxies
retain separate identities and historical bar-end, not vintage-certified, provenance.

## 3R.4 — actual forward evidence

**3 issued / 2 verified matured / 1 pending**, zero missed, one matured observation
per distinct inference cohort. November 6's pending forecast cannot mature before
November 7 00:00 UTC under the existing adapter bound and all original gates.
No future clock was supplied to force it. Repeated cycles do not backfill or
duplicate predictions/evaluations.

November 4 remains 553.443359375 points, P50 not covered, P80/P90 covered. November
5 remains 1471.7578125 points / original 28437.166015625 reference, all quantiles
missed; pinball P50/P80/P90 remains 0.017448145234075434 /
0.02131315690327859 / 0.01863813408992034. Expected quantiles, model/version,
issuance/source/evaluation timestamps and baseline comparisons remain separately
available in `reports/phase3i_forward.json` and immutable journals. Research-grade
unofficial-provider verification is not independently established exchange finality.
No calibrated forward accuracy or edge is inferred from two observations.

## 3R.5–3R.6 — acquisition is USER_ACTION_REQUIRED

Databento, FRED, BLS and Nasdaq Data Link keys are absent across the checked scopes.
No Databento authentication, entitlement/credit claim, cost quote or consumption
was attempted without access. Licensed NQ/ES receipts remain zero; quoted cost is
null, not zero. Current secret-free status: `reports/phase3r_data_access.json`.

The single exact acquisition checklist remains `PHASE3P_DATA_ACCESS.md`: operator
must configure an authorized key locally, verify GLBX.MDP3/CME license/entitlements,
run existing free metadata preflight, review exact per-contract quotes and approve
the bounded NQZ6/ESZ6 pilot before any metered or credit-consuming request. No adapter
was rebuilt and no blocked download loop was run. Minute/five-minute bars cannot
supply actual trades, bid/ask, volume-at-price/CVD or book reconstruction. Those
schemas each require suitable licensed data and separate quote/approval controls.

No genuine futures cycle, direction/consolidation/auction/200–500-point target-first
model or executable strategy performance can be reported. Sufficient independent
paths/events, realistic costs and calibration remain blocked; unsupported output
probabilities stay null and strategy eligibility stays NO_TRADE.

## 3R.7 — focused operational/security review

Found and fixed unsafe path-query handling in file-backed API endpoints. Instrument
and session inputs now reject path separators, absolute paths and overlong values
before filesystem access. Tests use an isolated outside-directory fixture and
confirm no mutation routes. Legitimate NQ/^NDX/NQ=F-style identifiers remain valid.

The API still has **no authentication, TLS termination, rate limiting or external
deployment/load approval**. CLI default binding is loopback; do not expose it
publicly. Input validation is a narrow security fix, not deployment authorization.
No accounts, passwords, security/logging policy or network/firewall settings changed.

A real recovery/scheduler collision was caught and retained: capture ran
01:46:58–01:47:09 while the 01:47 tick hit its guard, returning **75/BUSY_WRAPPER**,
not success. This was a backup-admission issue, not recurrence of 0xC000013A.
Capture now defers near actual task deadlines and live captures are bounded to
30 seconds. A racing wrapper waits up to 45 seconds for a shared backup byte lock;
another active wrapper still fails immediately. Windows tests cover both cases.
Failure evidence: `reports/phase3r_backup_collision.json`.

Subsequent genuine Task Scheduler completions and full lifecycle receipts are in
`reports/phase3r_scheduler.json`; no failed status was hidden or remapped. Existing
console-free scheduling is retained, not replaced. Tasks still require an awake,
interactively logged-in host; 0xC000013A's original sender remains unconfirmed.
Provider outage/retry/deadline/corruption contracts remain regression-tested, not
a guarantee against every real outage. Reboot/logoff, long soak, hard memory
isolation, independent paging and approved unattended deployment remain open.

## 3R.8 — acceptance

**NO-GO frontend.** Engineering evidence improved in offline dependency integrity,
exact frozen inference, bootstrap automation, backup coordination and input security.
Separate-host/off-host durability, operational cutover/rollback, approved unattended
availability, API access controls/load review and independent monitoring remain
partial. Quantitative acceptance remains blocked on authentic independent futures
history/events and sufficiently large forward cohorts. No arbitrary percentage or
predictive-readiness claim is assigned. See `BACKEND_READINESS.md` and
`reports/phase3r_acceptance.json`. Final local/isolated test and exact-SHA CI evidence
are recorded separately; fixture success is never market predictive validation.

Final local and isolated suites: **384 passed each**, including native parity;
TypeScript passed. All five CI jobs (Python, TypeScript, native, Windows-shadow,
Windows-locked-runtime) passed for `3a88a5d5215900404f431fed7f9b62d88e72aa7b`:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/42147434793
`reports/phase3r_ci.json` also retains the initial rejected workflow YAML incident;
it was fixed and now has a parser regression test. Later docs/evidence commits do
not change that tested implementation SHA.

A post-fix capture also exercised actual task-deadline admission successfully:
750 files/238,355,382 bytes, 9.51 seconds, checksum
`d20ef3280e9b57143fb00d7a7664c5f65918143c4120abf45ca8cc743586ad4d`.
Its evidence is separate in `phase3r_recovery_admission_*.json`; the original
688-file capture/collision is not overwritten or reclassified.
