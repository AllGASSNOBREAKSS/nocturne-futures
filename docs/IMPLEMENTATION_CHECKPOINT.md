# Implementation Checkpoint

## Current resume point — Phase 3T, 2026-11-08 UTC

Branch `feat/phase3t`, base `d69f853`, core implementation `fcac56c`, fix `6bd0f75`.
Read `PHASE3T_FINDINGS.md`, `BACKEND_READINESS.md`, `reports/phase3t_acceptance.json`
and both `phase3t_incident_*.json`. Baseline HEAD `d69f853` independently has all
five CI jobs green in run 42464563825. No frontend, paid consumption, broker
activation, numerical/model changes, source rewrites or new market-model fits.

Two incidents classified **OBSERVED_PROVIDER_REVISION_FINALITY_UNVERIFIED**;
both remain **AUDIT_BLOCKED**, unapplied. November 6 reference 26629.80859375 →
26629.810546875 (+0.001953125); November 9 reference 26989.9921875 → 26989.990234375
(−0.001953125). Raw source identity/session/adjustment conventions match, and exact
issued inputs replay. Independent final outcome high/low cannot be established;
FRED checks failed and Nasdaq unavailable/404. November 6 provider target bar is
present/available, but not independently final; November 9 also has not occurred.
Do not apply a candidate proof, rescale denominators or manufacture a maturity.
Disposition evidence is append-only/content-addressed in the private snapshot
archive; public per-forecast reports include timestamps, hashes, differences,
independent checks and exact blocking reasons. Investigation changed no journal.

Operational execution/issuance/integrity now have separate components. Fresh
completed quarantine is not a crash; aggregate health is still degraded. Fixed
precedence so concurrent generation failure cannot be hidden by historical audits.
Scoped shadow jobs now require exclusive per-attempt receipts. Completion with
historical quarantine retains exit 1, IDs, receipt hash and BLOCKED job health;
only a truly completed scoped operation releases its dependencies. Missing receipt,
failed refresh/issuance, exception/wrong exit are not forgiven. One-shot lock
contention returns 75. Existing Windows runner/actions/settings remain unchanged.

Local ack CLI extends `phase3j_operations.py` with `--ack-alert --actor --reason-code`;
state remains OPEN, no secret/free text, no gate bypass or HTTP mutation. Only
fixture acknowledgement was exercised; all four real alerts remain open. Existing
evidence-based monitor resolution is preserved.

Actual shadow lane executed five job types; concurrent research tick ran zero new
research jobs, correctly reusing cached work. Two report jobs updated; all 12 types
are inventoried in `phase3t_assurance.json`. No exhausted market fit/holdout tuning.
Two real exercised task completions each: shadow exit1, research exit0, complete
lifecycle receipts in `phase3t_scheduler.json`. Actual host still Interactive,
awake/logged-in only. Current state **4 issued / 2 verified matured / 2 pending /
0 missed / 4 open alerts**, one matured observation per inference cohort.

At `fcac56c`, local and isolated suites pass **429 tests**, native parity included;
TypeScript passes; all five CI jobs green in run 42465576451. Locked numerical
runtime/native build was reused, not rebuilt. 13,458 installed hashes and four exact
issued quantile cases verify (`phase3t_runtime.json`). Later assurance/report commits
need separately recorded CI; do not claim prior green applies automatically.
Fix `6bd0f75` (full-bar reconciliation blocks close-only fallback): 431 tests pass
locally and in new isolated env `C:/Users/huzai/AppData/Local/Temp/opencode/nocturne-phase3t-final`
(old phase3s-final venv python.exe missing again; cause unknown). Five CI jobs green,
run 42466314331. Live check 2026-11-09 01:47 UTC: scheduler still runs every 30 min,
shadow exit 1/AUDIT_BLOCKED, execution COMPLETED, 4/2/2/0, four alerts open.

Existing AES-GCM private archive restored into new approved temp destination
`C:/Users/huzai/AppData/Local/Temp/opencode/nocturne-phase3t-recovery/evidence`:
765 files, authenticated before extraction, replay20.64s, RESTORED_NOT_ACTIVATED.
It is the November 6 three-issue/two-outcome snapshot, not a latest-state backup.
Demo key remains separate/outside repo, not production independent custody.
OFF_HOST_VERIFICATION_REQUIRED; proposed RPO30m/RTO60m not achieved off-host SLOs.

External-access report `phase3t_external_access.json`: provider credentials absent
at checked process/user/machine scopes, licensed receipts0, quote/entitlements/
credits/IDs unknown, no paid consumption. Exact existing secure configuration and
bounded pilot approval are in `PHASE3S_FUTURES_PILOT.md` / `PHASE3P_DATA_ACCESS.md`.
Futures direction/consolidation/levels/100/200/350/500-point target-first research is
BLOCKED; probabilities unsupported/null. No new authentic strategy results.

Next dependent actions: provide verifiable independent final NDX outcome OHLC with
source/session/availability provenance for deliberate incident review; configure
entitled GLBX.MDP3 access and approve exact quotes; authorize private independent
recovery/key custody and unattended host/monitoring/security review. Continue actual
guarded issuance/audit/report cadence; do not rebuild working infrastructure or
repeat rejected models on unchanged data. NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.

## Historical resume point — Phase 3S, 2026-11-08 UTC

Branch `feat/phase3s`, base `504a168`. Implementation `b722033`, hardening `61878d5`,
current-blocker/report regressions `b75ee44`, alert/CI status normalization `b0364b9`.
Read `PHASE3S_FINDINGS.md`, `PHASE3S_SECURITY_DEPLOYMENT.md`,
`PHASE3S_FUTURES_PILOT.md`, `BACKEND_READINESS.md` and
`reports/phase3s_acceptance.json`. No frontend, broker activation, paid consumption
or new market-model fit. NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.

Protected API read/admin roles, private token files, request/rate bounds, fail-closed
secret-safe audits, health separation and isolated certificate-verified TLS work.
Admin has no write/job authority. Loopback remains default; no public deployment.
Read documented compatibility changes before restarting HTTP clients. Audit log
capacity is bounded and needs operator rotation; production ACL/TLS/security/load
review is not complete.

At `61878d5`, 406 tests pass locally and in isolated clean clone/venv (native parity
included); all five CI jobs pass in run 42153192576. TypeScript passes. Offline
security profile verifies 58 wheel hashes / 145,253,614 bytes and 13,458 installed
file hashes. Exact three original issued-row replay remains unchanged. Later
source/report commits require separately recorded CI; do not misattribute results.

Final replacement-environment suite at `c5de881`: **408 passed, no skips**, fresh
native build; local 408 also pass. Final report `phase3s_tests.json` records exact
test scope/durations. `phase3s_runtime_final.json` verifies all **four** issued rows
and 13,458 installed hashes. All five CI jobs are green at `c5de881`, run
42464277742 (`phase3s_ci.json`); `b75ee44` is also confirmed five-job green in run
42464001630. No source/model
changes followed the `c5de881` full isolated suite; remaining updates are evidence
and documentation only.

November 6 coherent snapshot: 765 files / 239,693,198 bytes, manifest
`b75aaffc57d18a8b0bd2781783253c5dc5fe44b5c5b4a537f12e7ed89ae5960f`.
Encrypted package `data/recovery/phase3s-encrypted-20261106-v1.nct` is private/ignored;
demo key is outside repository under the approved temp drill root, not production
key custody. Capture 14.14s, packaging 13.02s, authenticated restore/replay 23.70s.
Fresh source/venv/restored evidence are under
`C:/Users/huzai/AppData/Local/Temp/opencode/nocturne-phase3s-clean/`.
On November 8 the old drill venv's Python was missing (cause unknown), so a new
independent clone/environment was prepared under `nocturne-phase3s-final/`; the old
directory and original receipts were retained. See interruption report. Never
treat temporary drill directories as durable environments or backups.
RESTORED_NOT_ACTIVATED; same-host only; snapshot predates later appended state.
OFF_HOST_VERIFICATION_REQUIRED; proposed RPO 30m/RTO 60m are not achieved SLOs.

On November 8 resumption live scheduler had appended a fourth genuine forecast
`cd26071237a957cd7a874933` for November 9. Actual current state: **4 issued / 2
verified matured / 2 pending / 0 missed**. Pending November 6 and 9 reference bars
were revised upstream; integrity gates are **AUDIT_BLOCKED**. Existing investigation
tool reproduces issuance features and reports provider revisions, but independent
FRED/Nasdaq corroboration is unavailable. Two separate 3S revision reports remain
**unapplied**; forecasts/outcomes/denominators were not changed. The November 6
availability bound has passed, but do not create an outcome until all original
source/audit/maturity gates pass. Never automatically reconcile subsequent revisions.

November 6 repeated zero-exit task receipts remain in `phase3s_scheduler.json`.
Current `phase3s_scheduler_current.json` correctly records shadow exit **1** with
complete lifecycle, research exit **0**; four open alerts/core degraded. Do not
claim healthy scheduling solely from older successes. Actual deployed tasks remain
Interactive/awake/logged-in; installers' Password/startup support was dry-run only.

Next: deliberate evidence-bound source review and full audits (no forced overrides),
continue genuine timestamped operations, configure Databento securely and approve
exact quotes before any bounded licensed pilot, obtain approved unattended host,
private off-host destination/key custody and independent monitoring/security review.
Keys absent at checked scopes; licensed receipts zero; costs/entitlements unknown.

## Historical resume point — Phase 3R, 2026-11-06 UTC

Branch `feat/phase3r`, base `c65e596`. Read `PHASE3R_FINDINGS.md`,
`PHASE3R_REPRODUCIBILITY.md`, `BACKEND_READINESS.md` and
`reports/phase3r_acceptance.json`. Implementation commits: `bef69f2`, `3f1dea3`,
`d0aaad3`, `878ae6d`, `3a88a5d`. Final tested source is `3a88a5d`; all five CI jobs
passed in run 42147434793. Initial workflow YAML failure is retained, not hidden;
block-scalar fix and workflow-parse regression prevent recurrence.

55 exact Windows/CPython-3.14 wheel hashes verified against PyPI, then a new venv
installed offline and built native C++20 freshly. 13,290 installed RECORD hashes
verify; all three issued quantiles replay exactly with cohorts separate. Frozen
loader now rejects unapproved six-library numerical versions before pickle load.
Final local and clean isolated suites each pass 384 tests including native parity;
TypeScript passed. Frozen model/old journal prefixes remain unchanged.

Same-host private recovery verifies source proofs, 3 forecasts/2 outcomes, six cached
challenger files and two old fixed diagnostics. Snapshot v1: 688 files/231,067,330
bytes; local restore 13.70 seconds. This capture caused a real 01:47 scheduled
BUSY_WRAPPER/75; preserve `phase3r_backup_collision.json`. Capture now checks real
task deadlines, limits live-host work to 30s and defers near ticks. Wrappers wait
boundedly for backup byte locks but reject true overlap. Subsequent two runs per
task have zero exits and complete lifecycle receipts. No task configuration or
host security settings changed. Existing awake/logged-in limitation remains.

An additional v2 snapshot passed the new real deadline admission: 750 files /
238,355,382 bytes in 9.51s, checksum
`d20ef3280e9b57143fb00d7a7664c5f65918143c4120abf45ca8cc743586ad4d`.
See `phase3r_recovery_admission_*.json` for its verification, separate from the
retained v1 collision. Do not activate either restored copy.

Forward counts still **3 issued / 2 verified matured / 1 pending**, one matured per
cohort. November 6 cannot mature before November 7 00:00 UTC and original gates.
No backfilling, model fitting, holdout tuning, paid consumption or frontend/live
orders. Five real shadow orchestrator job types executed; research tick correctly
reused existing validation. All 12 kinds inventoried in `phase3r_assurance.json`.

Futures acquisition: **USER_ACTION_REQUIRED**, no keys/entitlements/quote/approval,
zero licensed receipts. Use the single checklist `PHASE3P_DATA_ACCESS.md`. Do not
rebuild adapters or retry blocked downloads. Direction/target-first models remain
unvalidated; old negative index diagnostics are not NQ/ES execution results.

API file-backed path-query handling is hardened and tested; API still lacks
authentication/TLS/rate limits/deployment approval. NO-GO frontend pending genuine
futures/independent calibration samples, approved unattended availability and
monitoring, API security/load review, hard memory isolation and authorized
encrypted off-host/separate-host recovery/cutover. Proposed RPO 30m/RTO 60m are
not achieved off-host SLOs. No authorized independent private-recovery destination
was supplied; hosted CI verifies public-code bootstrap/inference only, not archives.

Resume with actual clock/task receipts and guarded refresh/audits/reports; preserve
all automatic changes and incidents. Runtime/wheel upgrades need a separate
candidate and unchanged exact replay. Do not relax checks or edit expected history.

## Previous resume point — Phase 3Q, 2026-11-06 UTC

Branch `feat/phase3q`, base `84a4ea9`. Runner implementation `be54b5b`; pinned
environment tooling `e061c46`; runtime/acceptance gate `001d55b`. Read `PHASE3Q_FINDINGS.md`, `PHASE3Q_DEPLOYMENT.md`,
`BACKEND_READINESS.md` and `reports/phase3q_acceptance.json`. Preserve all automated
changes. No frontend/live execution, new market-model fitting or paid data.

Current forward state: **3 issued / 2 verified matured / 1 pending**, one legacy
and one corrected matured outcome. November 5 matured honestly after the bound:
range 1471.7578125 / original reference 28437.166015625; all quantiles missed.
November 6 forecast `291aac9c9d893a888609aafd` is pending. Prior journal bytes remain
unchanged prefixes; frozen model hash unchanged. Any new revision still blocks
unless deliberately proven under original gates; never backfill predictions.

Hidden PowerShell alone failed one of three scheduled shadow tests. Console-free
pythonw + CREATE_NO_WINDOW now wraps existing runners: three actual completions
per task, all exit 0 with fsynced launcher/runner receipts. The normal automatic
01:17 UTC shadow tick also completed with exit 0 (`phase3q_timed_shadow.json`).
Sender of old
STATUS_CONTROL_C_EXIT remains unconfirmed (Task Scheduler history disabled).
Only task Actions changed; original XML privately archived; settings/principals/
triggers unchanged. Still Interactive/awake/logged-in only; no 24/7 or reboot/logoff
proof. Inspect `phase3q_scheduler.json`, retained failed hidden experiment and
`phase3q_host_diagnostics.json`; do not infer scheduling health from core reports.

Local tests: 362 passed including native parity; fresh independent clone + pinned
venv/native build: 362 passed/no skips. TypeScript and installer dry runs passed.
Broad clean dependency upgrades passed fixtures but failed real issuance proofs;
pinning NumPy 2.5.0/pandas 3.0.3 restores exact checks. Never loosen those checks.
All package/native paths and pins attested in `phase3q_environment.json`.

New private snapshot: 654 files / 228,647,450 bytes, ignored
`data/recovery/phase3q-local-20261106-v1`. Restored proof in approved private temp
area using clean venv verifies 3 forecasts/2 outcomes/six cached challenger hashes
and two exact old index diagnostics. One genuine nine-source validation job also
ran from newly initialized empty SQLite state. No original evidence was mutated.
This is still same-host: no authorized off-host location, separate OS/host,
service-account activation or cutover/rollback test. Old SQLite artifact paths are
absolute: mapped offline replay is not automatic relocated live job resumption.

Acquisition: **USER_ACTION_REQUIRED**; four provider keys absent across scopes;
zero licensed rows, cost/entitlement/credits unknown. Use the single exact checklist
`PHASE3P_DATA_ACCESS.md`; do not rebuild adapters or retry blocked downloads.
NO-GO frontend pending deployment/off-host/monitoring/API-security/memory-isolation
gates plus authentic independent futures/calibration/sample evidence.

Resume: check actual clock and task lifecycle receipts, refresh/evaluate through
the existing sole live runtime, run audits/reports and `phase3q_acceptance.py`.
Do not activate the isolated restored copy or re-run old index fitting. Verify
Phase 3Q CI against its exact pushed SHA: `001d55b` passed all four jobs in run
42142381461 (`reports/phase3q_ci.json`). Later observation/docs commits do not
change the tested implementation.

## Previous resume point — Phase 3P, 2026-11-05 UTC

Branch `feat/phase3p`, base `ce76bf6`. Read `PHASE3P_FINDINGS.md`,
`PHASE3P_DATA_ACCESS.md`, `BACKEND_READINESS.md` and `reports/phase3p_evidence.json`.
355 local tests/native parity and TypeScript passed. Implementation `8994d9e`
was pushed; all four CI jobs passed in run 42131793179. Later evidence/docs commits
must be distinguished from the implementation SHA tested by that run.
New bounded local recovery drill: 547 files, 210,599,711 bytes; original proof,
outcome and six cached challenger hashes verify after separate-location restore.
Two existing fixed authentic index diagnostics reproduce exactly, not new research.
No model retrained or newly exposed holdout scored. No frontend/live execution.

Before November 6 00:00 UTC: two issued, one verified legacy matured, one pending
corrected forecast. Do not force maturity; refresh/evaluate only at actual eligible
time and retain audit blocks on any new source change. Verify forecast/outcome/model
bytes against base with `python scripts/phase3p_evidence.py`.

Current scheduling caveat: direct shadow runner exits 0, but both scheduled tasks
return 3221225786 / 0xC000013A on explicit launches. Scheduling DEGRADED; root cause
unconfirmed. Do not infer healthy scheduling from healthy core reports. Definitions,
principals and security settings unchanged; no 24/7 claim. Inspect complete stage
receipts and host termination evidence before calling this recovered.

Futures remains externally BLOCKED: four provider keys absent; free preflight
returns unknown quote/no consumption, zero licensed rows. Operator must configure
GLBX.MDP3 access and approve actual exact quotes before the existing bounded pilot.
Remaining gates: independent futures/target evidence, enough corrected forward
outcomes, reliable schedules, clean-host/off-host restore, authorized monitoring/
availability, process-memory isolation and API security/load review.

Ignored snapshot `data/recovery/phase3p-local-20261105-v2` and separate temporary
restore are same-host proof only, not durable off-host backup. Keep manual evidence
writers quiescent for future snapshots. Never overwrite restored/live state.

## Previous resume point — Phase 3O, 2026-11-05 UTC

Branch `feat/phase3o`, base `8065a34`. Read `PHASE3O_FINDINGS.md`,
`reports/phase3o_reconciliation.json`, `reports/phase3o_operations.{json,md}`,
`PHASE3O_DATA_ACCESS.md` and the pre-frontend gates in `BACKEND_READINESS.md`.
Phase 3N CI verified green and 342 tests reproduced. New local suite:
**348 passed including C++ parity**; TypeScript passed. Check branch CI after push.

Reconciled forecast `3db9c4cbd3a9cc5944db8437` deliberately using its embedded
issuance snapshots, record seal, exact features/dataset digest and preserved
pre-issuance receipts. November 4 OHLC and volume changed; close
28437.166015625 → 28437.169921875. Timestamp/index/session conventions match,
quote and adjusted close agree. FRED timed out; Nasdaq returned 404. Decision:
VERIFIED_AS_ISSUED_PROVIDER_REVISION, not confirmed exchange truth/internal cause.

Separate proof appended; forecast/outcome bytes and denominator unchanged. New
proof seals the full revised reference bar, so same-close volume/OHLC changes
must block again. Missing/corrupt archive or changed forecasts also block. The
real cycle passed and alert journal appended RESOLVED events without erasing OPEN
history. Latest proof reverified every cycle; no tolerance inflation or automatic
approval of future revisions. First outcome stays its original archived value.

As of this checkpoint: **2 issued / 1 verified matured / 1 pending**, one legacy
matured and zero corrected-inference matured. November 5 outcome cannot be
scored before November 6 00:00 UTC and valid completed data. Never backfill it.

Fixed nested health masking recent audit failure behind older success. Added
component statuses, explicit DISABLED/DEPENDENCY_BLOCKED versus real FAILED
states and timestamped job health. Fifth shadow-runner stage writes unified
health snapshots/history. Core can be healthy while futures dependencies are
blocked; that is not full platform or trading readiness.

Actual nine-source archival validation job SUCCEEDED. Default unchanged research
did not refit/rescore old index models. Seven-job subprocess integration passed
in explicitly synthetic temporary storage; no fixture enters live journals.
Tests cover outage/block distinction, disabled dependencies, incident recovery,
full-bar revision reblocking, corrupt evidence and existing deadline/restart rules.

```powershell
python scripts/phase3o_reconcile.py --forecast-id 3db9c4cbd3a9cc5944db8437  # inspect, no journal writes
python scripts/phase3o_health.py
python scripts/phase3m_research.py --lane research
```

Existing task definitions/principals/security unchanged. Awake host plus interactive
login still required; actual reboot/logout/off-host failover remains unverified.
Do not treat successful same-host task checks as 24/7 availability.

Credentials absent in process/user/machine scopes; zero licensed NQ/ES rows,
provider cost/range/IDs/credit eligibility unknown. Do not attempt authenticated
downloads until operator configuration. Existing quote-bound approval and no-
blind-retry reservation controls remain unchanged. No new market models justified.
Next: operator configures GLBX.MDP3 license/key, obtains/approves actual pilot
quote, validates raw pilot provenance, then sufficient independent futures history.
Private snapshot/journal/SQLite backup and clean-host recovery, unattended/paging
and API deployment security remain pre-frontend gates. NO_PROMOTION / NO_TRADE.

## Previous resume point — Phase 3N, 2026-11-05 UTC

Branch `feat/phase3n`, base `2dcec42`. Read `PHASE3N_FINDINGS.md`,
`PHASE3N_DATA_DECISION.md`, `ARCHITECTURE_PHASE3N.md`, `BACKEND_READINESS.md`
and `reports/phase3n_futures_access.json`. Phase 3M CI verified green at
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41954993266
New local suite: **342 passed including native parity**; TypeScript passed.
Verify this branch's CI after push.

Highest-priority dependency remains **DATA_BLOCKED**: keys absent in process,
user and machine scopes; NQZ6 and ESZ6 each have zero licensed rows. All supplied
official pages returned 200 and are privately hash-archived. Free metadata and
symbology interfaces are documented; account credit eligibility, entitled schema
range, resolved IDs and actual provider count/size/cost remain unknown/null.
No authenticated or paid request, subscription or cloud deployment occurred.

Implemented metadata-only preflight and strict quote/explicit operator approval
on the existing bar adapter. Consumption is durably reserved before the network
under a request lock; uncertain attempts block blind charged retry. Rejected raw
bodies and bounded partial prefixes are retained. New receipt replay rechecks
archived quote/approval bindings and mapped provider ID. Timestamp, volume, ticks,
count/revision and bounded-response checks precede normalized publication.
Quotes are estimates, not provider-enforced final-invoice caps.

Existing orchestrator now connects verified contract receipts to ORB/bar-VWAP
engine diagnostics and separate target labels. Full fixture path works; actual
NQ/ES jobs returned BLOCKED with null directional/target/survival results. Default
scheduled research checks both explicit pilot contracts but never downloads data.
Futures job identity is shared by the CLI and scheduler and stable across dates
for identical receipts/code. Old index diagnostics now require explicit
`--index-diagnostics`; the default no longer repeats insufficient-data experiments.
No old index experiment was refitted and no holdout rescored. Bar-VWAP is a proxy;
true profiles/CVD/depth/absorption remain unavailable. Cashflow-v2 fixes double
entry-slip and fill-count commission arithmetic in the existing engine; legacy-v1
results/default remain for reproduction. Trade records carry the version. Real
execution assumptions and intrabar bounds still need independent validation.

Forward state remains **2 issued / 1 verified matured / 1 pending**; one legacy
matured sample, zero corrected-inference matured. Forecast/outcome/model bytes
preserved. November 5 is pending until November 6 00:00 UTC and verified data.
On resume November 5 afternoon, the shadow task correctly failed its source audit:
forecast `3db9c4cbd3a9cc5944db8437` stored November 4 close 28437.166015625, while
Yahoo now reports 28437.169921875. Retain AUDIT_BLOCKED / REFERENCE_CLOSE_MISMATCH
and both durable open alerts; do not silently reconcile or change the denominator.
Latest inspected task results: research 0, shadow 1. First matured outcome still
verifies from its saved snapshot, which does not clear this new pending-forecast
incident. Reports expose the operations snapshot separately. No schedule,
principal or security setting changed; awake host/interactive login still required.

```powershell
python scripts/phase3n_futures.py --public-docs --research-check # metadata only; expected exit 1 without key
python scripts/phase3m_research.py --lane research
python scripts/phase3l_forward_audit.py
```

Do not delete consumption reservations to force retry. Back up private
`data/licensed/databento_metadata/`, guarded bar approval/raw/partial/receipt
objects and orchestrator SQLite/attempt history consistently. Git cannot restore
these private proofs. No approved-consumption file was created by the agent.

Next: operator verifies GLBX.MDP3 license/credit terms, configures a local key,
runs the free preflight and approves its exact quote explicitly. Then bounded
NQZ6/ESZ6 acquisition, ID/grid/calendar/availability validation, authentic diagnostic
and only later sufficient-history feature ablation/independent model research.
Also investigate the second forecast's archived issuance/current source revision
with the existing hash-bound reconciliation policy before evaluating its outcome.
All unvalidated models remain NO_PROMOTION / NO_TRADE. No frontend work.

## Previous resume point — Phase 3M, 2026-11-05 UTC

Branch `feat/phase3m`, base `6c04c50`. Read `PHASE3M_FINDINGS.md`,
`ARCHITECTURE_PHASE3M.md`, `BACKEND_READINESS.md` and
`reports/phase3m_research.json`. Phase 3L's 291 tests and CI were reproduced.
New local suite: **311 passed including native parity**; TypeScript passed.
Check Phase 3M CI after push rather than assuming the prior phase's green run.

Implemented persistent SQLite jobs/DAG/retries/backoff/recovery, separate research
and shadow process/lock lanes, bounded workers/watchdogs, versioned datasets,
fixed cached logistic experiments and JSON/Markdown history. All twelve requested
job types have actual handlers; raw futures jobs remain explicitly blocked.

Executed nine source validations, two 6,036-row index-context backtests and two
three-fold calibrated logistic diagnostics (750 development test predictions
each). NDX Brier 0.249911 vs baseline 0.249863; S&P Brier 0.248798 vs 0.249196.
No independent validation or new directional/target promotion is claimed. Old
development exposure and excluded 2024+ history are not relabeled untouched.

Deployed `Nocturne-ReadOnly-Research` every six hours + logon, interactive and
limited, 18-minute cap; observed exit 0. Original 30-minute shadow task unchanged,
observed successful. Research cadence enqueues daily keys; identical experiment
identity reuses model/results without fitting again. Host must be awake/logged in.

Forward state: **2 issued, 1 verified matured, 1 pending, 0 missed**. All forecast
bytes remain identical to Phase 3L; model weights unchanged. November 5 pending
cannot mature before the November 6 00:00 UTC availability bound. Legacy matured
cohort is one; corrected-inference matured cohort is zero. NO_PROMOTION / NO_TRADE.

```powershell
python scripts/phase3m_research.py --lane research
python scripts/phase3m_research.py --lane research --no-enqueue
python scripts/phase3m_research.py --lane shadow  # reuse existing idempotent cycle; not a second scheduler
```

Private `data/research/orchestrator/` holds SQLite, attempts, reports, datasets,
code snapshots and challenger artifacts. Back up consistently with market source
archives; Git alone cannot restore proofs or running-state history. Do not erase
failed/partial experiments: incomplete cache directories require operator review.
Original validation schema failure and recovery remain in transition history.

Data access unchanged: no credentials in checked process/user/machine scopes;
no paid request. See `DATA_ACQUISITION_PHASE3M.md` for entitlement, quote uncertainty
and exact pilot. Next: authorized raw-contract pilot, validate session/roll/PIT
evidence, expand history and run real session-strategy/feature ablations. Remaining
independent deployment work: unattended authorization, hard memory quotas,
off-host monitoring, retention/private backups and clean-host recovery validation.
No arbitrary overall readiness percentage or trading-readiness claim was assigned.

## Previous resume point — Phase 3L, 2026-11-05 UTC

Branch `feat/phase3l`, base `262c4dc`. Read `PHASE3L_FINDINGS.md`,
`reports/phase3l_forward_audit.json` and `reports/phase3l_readiness.json`.
Phase 3K reproduced 265 passing tests and verified green CI. New local suite:
**291 passed including native parity**. Check Phase 3L's own CI after push.

Actual scheduler progress: **2 issued / 1 verified research-grade matured /
1 pending / 0 missed**. First outcome `20d48fc41c2cc0f5c0ae4f2d` was appended
November 5 00:17:10 UTC, from a completed November 4 daily snapshot received
00:17:09 UTC. High 28829.662109375, low 28276.21875, range 553.443359375 points,
fraction 0.019639396061696825 using original reference 28180.263671875.
P50 not covered; P80/P90 covered. Pinball details are in the audit report.

Original forecast line hash is unchanged. The outcome is legacy unadjusted
inference; corrected inference has **zero matured observations**. One result is
descriptive, never calibration success or a trading signal. First baseline
comparison is explicitly post-issuance, frozen before outcome, not a retrofitted
issued forecast. No journal fields were changed to insert it.

The next forecast `3db9c4cbd3a9cc5944db8437`, target November 5, was issued
November 5 00:17:12.620017 UTC, before the 14:30 UTC cash open. It remains pending.

Added independent outcome verification/quarantine and timestamped read-only API,
receipt-based single-contract replay, causal session-state context and NQ point/
horizon target labels. Actual licensed inventory remains empty; target rows are
zero outside fixtures, probabilities remain null and no models were promoted.

AJ censoring hazard bug, observation-end handling and late-published-bar ATR
leakage were corrected. AJ-v1 reports remain historical and require recomputation;
this is not a new authentic-data fit. Historical latency/vintage, authoritative
calendar/roll evidence and true order-flow inputs are still required.

Credentials absent in process/user/machine scopes. FRED DGS10 and BLS CPI probes
now succeed; their current vintages remain PIT-ineligible. FRED NASDAQ100 has no
November 4 observation in the probed response. Cost quote requires authenticated
provider metadata and entitlement; no purchase or licensed request was made.

```powershell
python scripts/phase3l_forward_audit.py       # reports only; never rewrites journals
python scripts/phase3i_forward_report.py
python scripts/phase3j_operations.py
python scripts/phase3l_readiness.py --probe-context
python scripts/phase3l_contract_replay.py --instrument NQ --contract NQZ6 --asof 2026-11-02T16:00:00Z --day 2026-11-02
```

Last command is expected to return DATA_BLOCKED until authentic private receipts
exist. Keep snapshots/private data backed up outside Git. Diagram/source:
`ARCHITECTURE_PHASE3L.md`. Windows interactive task remains; no credentials or
privileges were changed. Unattended deployment/off-host paging remain separate.

Next: authorized GLBX.MDP3 entitlement + exact cost quote, ingest the documented
one-session NQZ6/ESZ6 pilot, validate receipts/grids/calendar/availability, then
expand history before feature ablation/model fitting. Await the November 5 outcome
after November 6 00:00 UTC and accumulate genuine corrected-inference samples.
Do not retrain the frozen model or enable orders. All trading remains NO_TRADE.

## Previous resume point — Phase 3K, 2026-11-04 UTC

Branch `feat/phase3k`, base `9f68c6b`. Read `PHASE3K_FINDINGS.md` and
`reports/phase3k_reconciliation.json`. Phase 3J reproduced 253 passing tests and
green CI. Phase 3K local verification: **265 passed including C++ parity**;
TypeScript typecheck passed. Check this branch's own CI after push.

Source incident: original raw/normalized hashes and pre-issuance receipt times
verified; archived inputs exactly reproduce all stored features and digests.
Yahoo changed November 3 OHLC **and volume**, not the session timestamp or index
identity. Quote and adjusted close coincide in both versions. Classification is
`VERIFIED_AS_ISSUED_PROVIDER_REVISION`; internal provider reason and official
exchange finality remain unconfirmed. FRED connection failed and Nasdaq endpoint
returned 404; no independent confirmation is claimed.

Separate reconciliation records bind the original forecast hash to immutable
issuance/revised snapshots. The audit re-verifies proof each cycle and permits
the as-issued original reference 28180.263671875; it never substitutes the
revised close. Original forecast line/hash and model artifacts remain unchanged.

Immutable content-addressed archives are under ignored
`data/shadow/market/snapshots/`. Preserve/back up this directory along with the
forecast, reconciliation and alert journals. Repo clone alone is not an archive
backup. New forecasts require exact snapshot versions; checksum-pinned model
weights/metadata and a `FROZEN` research guard reject silent replacement.

Forward state: **1 issued / 0 matured / 1 pending / 0 missed**. Latest real data
still ends November 3; November 4 has not opened. No forward metrics exist.

```powershell
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3i_forward_report.py
python scripts/phase3j_operations.py
python scripts/phase3i_readiness.py
```

Do not rerun the old freeze script over the pinned model. Use artifact auditing
without fitting. Only run `phase3k_reconcile.py` for a deliberate evidence review;
it appends evidence, never forecasts/outcomes. Missing/changed archives or a new
unreconciled revision must block evaluation again.

Next: genuine completed November 4 outcome after the November 5 00:00 UTC adapter
bound, subject to all quality/provenance checks; then accumulate actual future
samples without tuning. Licensed futures/PIT dependencies and authorized
logout-independent deployment remain blocked. Trading stays `NO_TRADE`.

## Previous resume point — Phase 3J, 2026-11-04 UTC

Branch `feat/phase3j`, base `0c56df7`. Read `PHASE3J_FINDINGS.md` first.
Phase 3I reproduced 242 passing tests and verified green CI. Phase 3J local
verification: **253 passed including C++ parity**, TypeScript typecheck and both
interactive/unattended task-definition dry runs passed. Inspect this branch's
own CI result rather than using prior CI as evidence.

Code commit `68424a9` is pushed and passed all four CI jobs (Python, TypeScript,
native and Windows shadow/unattended-definition dry run):
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41778105510
The installed interactive task actually ran at 2026-11-04 05:17 UTC and returned
exit 1 for the persisting reference-close audit block. Its refreshed reports and
deduplicated open alerts are checkpointed separately; this is observed failure
handling, not a matured outcome or proof of unattended-after-logout operation.

Forward state: **1 issued / 0 matured / 1 pending / 0 missed**. Original journal
hash and model artifacts unchanged. Real refresh at ~05:07 UTC still ends
November 3. November 4 has not opened; do not invent an outcome.

New blocker: current source close 28180.259765625 differs from issued reference
28180.263671875. The first forecast remains quarantined with
`REFERENCE_CLOSE_MISMATCH`; review archived issuance evidence before any eventual
evaluation. Never edit the original reference or relax the audit silently.
Failed records are now quarantined individually, not as a global evaluation stop.

Added local OPEN/RESOLVED alert journal, 90-minute cycle staleness assessment,
overdue-outcome/provider/deadline alerts, `/v1/shadow/operations`, sanitized
one-shot failure status and per-stage scheduler logs. Real wrapper run exited 1
for the actual audit block and recorded two alerts; this is correct failure
reporting, not a successful market evaluation. No external paging is configured.

Unattended password-backed installer support is implemented but **not deployed**:
no authorized PSCredential was supplied. Existing interactive task is unchanged.
Dry-run does not establish account rights, network access or logout operation.
Review dedicated account, batch-logon, least-privilege ACLs and always-on host
requirements in `PHASE3J_FINDINGS.md`. An off-host watchdog is still required.

```powershell
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3i_forward_report.py
python scripts/phase3j_operations.py  # nonzero while actual audit block persists
```

Next: reviewed source-revision reconciliation, genuine completed-bar evaluation
after the November 5 00:00 UTC adapter bound, then authorized unattended rollout.
Licensed futures/PIT dependencies remain absent. No promotions or orders.

## Previous resume point — Phase 3I, 2026-11-04 UTC

Branch `feat/phase3i`, base `e963981`. Read `PHASE3I_FINDINGS.md` first.
Local verification: **242 passed including native C++ parity**. Base CI was
verified green. Current commit and remote CI: inspect `git log -1` and the
`feat/phase3i` Actions run; do not substitute base CI for new changes.

Engineering commit `92cd098` is pushed and passed all four CI jobs: Python,
TypeScript, native parity and Windows shadow/task dry run. Run:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41775767199
Follow-up hardening adds live API staleness/health, outcome history and scanning
of the actual private Databento receipt layout with checksum checks; its local
suite is 242 passing. Check the follow-up commit's own Actions result separately.

Forward state remains **1 issued / 0 matured / 1 pending / 0 missed**. Original
timestamp is `2026-11-04T02:53:30.237804+00:00` (supersedes the older 02:50 text
below). Journal bytes match `e963981`; never change the first forecast.

Important defect: original runtime omitted frozen residual adjustments. Fixed
runtime uses `inference_revision=residual-adjusted-v1`; original remains
`legacy-unadjusted` and must be scored separately, exactly as issued. No
retraining; original model/metadata unchanged. Runtime reproduces stored metrics
on the already-used 712-row holdout. This does not create independent evidence.

Windows task `Nocturne-NDX-ReadOnly-Shadow` was registered: 30-minute runs plus
logon, current logged-in user only. Host must be awake. Inspect actual task
result; registration alone is not demonstrated ongoing operation. Disable with
`Disable-ScheduledTask -TaskName Nocturne-NDX-ReadOnly-Shadow` when needed.

Observed scheduled cycle: 2026-11-04 04:47 UTC, exit code 0, fresh receipts,
`ALREADY_ISSUED`, no duplicate. This is one observed cycle, not an uptime history.

```powershell
Get-ScheduledTask -TaskName Nocturne-NDX-ReadOnly-Shadow | Get-ScheduledTaskInfo
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3i_forward_report.py
python scripts/phase3i_readiness.py
$env:PYTHONPATH='D:\nocturne-futures\native\build'; python -m pytest -o addopts=''
```

Real refresh ended November 3. November 4 outcome is not available before its
completion/availability bound (November 5 00:00 UTC in this adapter). No forward
performance statistics exist. Operational market cache is separate and ignored;
receipt/checksum/completeness checks forbid fallback to frozen research data.

Next: verify real scheduled exit/refresh, append the first verified matured
outcome, accumulate corrected-inference samples without tuning, and obtain
Databento entitlement. Databento/FRED/BLS keys are absent; authentic futures,
order flow and authorized PIT calendar/news remain blocked. Contract-target and
schedule-proximity modules are tested infrastructure, not validated forecasts.
Only NDX range is shadow-active; all other models remain `NO_PROMOTION`, trading
remains `NO_TRADE`. Phase 3I is an engineering checkpoint, not full acceptance of
future-dependent statistical or logout-independent production requirements.

## Previous resume point — Phase 3H, 2026-11-04

Branch `feat/phase3h`, base `016d5d0` (Phase 3G, CI success).
Read `PHASE3H_FINDINGS.md`, `FUTURES_DATA_REQUIREMENTS.md` and
`PHASE3G_FINDINGS.md` before changing anything. Decision remains **NO_TRADE**.

Implemented: frozen NDX range artifact with holdout reproduction, immutable
append-only shadow store, fail-closed eligibility, maturation-only evaluation,
run-once and loop scheduler, forward monitoring report, and read-only API
endpoints for shadow status/history/evaluation/data health.

**Forward state:** 1 forecast stored (`20d48fc41c2cc0f5c0ae4f2d`, target
2026-11-04, generated 2026-11-04T02:50Z), 0 matured. Do not claim forward
accuracy. After the 2026-11-04 session bar becomes available (2026-11-05 00:00
UTC), run:

```powershell
python scripts/phase3h_shadow.py --evaluate-only --refresh
python scripts/phase3h_shadow_report.py
```

That appends exactly one outcome and updates the report. Never edit
`data/shadow/ndx_range/forecasts.jsonl` or `outcomes.jsonl` by hand.

Reproduce and verify:

```powershell
python scripts/phase3h_freeze_model.py     # must reproduce the holdout within 1e-6
python scripts/phase3h_shadow.py --once
python scripts/phase3h_shadow.py --loop --interval-minutes 60 --refresh
python scripts/phase3h_shadow_report.py
$env:PYTHONPATH='D:\nocturne-futures\native\build'; python -m pytest   # 212 passed
```

Operational market cache `data/shadow/market/` is gitignored so frozen research
history is never overwritten. The forward journal is committed.

Next Phase 3I milestone: accumulate >= 30 matured forward predictions before
reporting coverage; in parallel obtain Databento `GLBX.MDP3` entitlement and
ingest a bounded raw-contract sample per `docs/FUTURES_DATA_REQUIREMENTS.md`.
Direction and target-before-stop models stay `NO_PROMOTION` until licensed
order-flow data exists.

**Date:** 2026-11-04
**Previous branch:** `feat/phase3g`
**Latest backend commit:** see `git log --oneline -1`
**CI:** `04def4b` passed all jobs (python, typescript, native).

## Phase 3A — backtest validation and predictive foundation

Completed on 2026-11-03:

- Reproduced the suite: **154 passed + 1 native skip**; **155 passed** with the
  C++ module on PYTHONPATH.
- Built the C++20 `nocturne_native` kernel with MSVC 19.51 and pybind11 3.1;
  the parity test passes. CI now has an Ubuntu native build/parity job.
- Fixed backtest accounting: commission per partial exit, `gross_dollars`,
  `costs`, `risk_points`, `mfe_r`, `mae_r`, `stop_price`, `target_prices`.
- Added conservative rules: one target per bar, gap-beyond-target skip, RTH-only
  session bars, config validation, target-side validation.
- Added regression tests for gaps, stop/target ambiguity, session boundaries,
  costs, NQ vs ES sizing, partial exits, timeouts and rolls.
- Cached 60-day 5m NQ/ES bars with SHA-256; the study is reproducible.
- Ran the held-out, cost-stressed study across NQ/ES × ORB/VWAP/value.
- Diagnosed the ORB timeouts (40 in the original ledger, 41 after the RTH-only
  fix): median risk 208.9 points, median MFE 0.26R, 4.5% reach 1R, 0% reach 2R,
  41/41 timeouts below 1R.
- Audited four label geometries: frequency wins every Brier comparison; the
  lower Brier in tight-stop/long-horizon configs is class imbalance.
- Added the target-level dataset interface and four committed datasets.
- Added `reports/ml_audit_NQ.md`, `reports/phase3a_backtests.md`,
  `docs/PHASE3A_FINDINGS.md`.

Verification commands:

```bash
python -m pytest -q
python -m nocturne study
python -m nocturne dataset --instrument NQ --strategy vwap
python scripts/ml_audit.py
PYTHONPATH=native/build python -m pytest tests/test_native_parity.py -q
```

Blocked: true tick/DOM/volume-at-price, CFE VX futures, point-in-time calendar.

Next exact step: train a target-first model on
`data/research/target_dataset_NQ_vwap.csv` with a chronological split; require a
holdout Brier improvement over frequency before adding features.

## Phase 3B — predictive intelligence V1

Completed on 2026-11-03:

- Added point-in-time intraday features: time of day, ATR, realized vol, OR/IB
  size, distance from VWAP/POC/VAH/VAL/session/prior/overnight levels, momentum,
  trend strength, range compression, volatility percentile, ES/NQ relative,
  VIX, risk/target ATR.
- Added signal-grouped chronological splits so multiple targets from one signal
  never cross train/test.
- Combined VWAP + revised-ORB + value datasets: 123 binary rows from 75 signals,
  base rate 0.520. Test: frequency Brier 0.2688, logistic 0.2735, GBM 0.2447;
  GBM AUC 0.4107, ECE 0.1535. **NO_PROMOTION** due to class shift and no ranking
  skill.
- Added `price_levels/engine.py`: prior RTH/week, overnight, Asia/London/NY,
  IB/OR, POC/VAH/VAL, HVN/LVN, VWAP/vol bands, 8-tick clustering, empirical
  touch/reaction stats.
- Added `research/range_model.py`: empirical forward-range quantiles by ATR
  bucket; NQ p50 260, p80 402, p90 512; P(≥200) 0.705, P(≥350) 0.270,
  P(≥500) 0.112.
- Added `regime.py`: ADX/efficiency/overlap/vol-percentile state and empirical
  transition probabilities. Current NQ state: COMPRESSION.
- Added `forecast/v1.py` and `GET /v1/forecast/v1`; research-only contract with
  null probabilities and `decision=NO_TRADE`.
- Added `docs/PHASE3B_FINDINGS.md`, `reports/phase3b_target_model.md/json`.

Verification commands:

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python scripts/train_target_model.py
python -m nocturne forecast-v1 --instrument NQ
python -m nocturne levels --instrument NQ
python -m nocturne range --instrument NQ
python -m nocturne regime --instrument NQ
```

Blocked: authentic tick/DOM/volume-at-price, CFE VX futures, point-in-time
calendar. No model or forecast is promoted.

Next exact step: expand the target dataset beyond 60 days, rerun the grouped
target model with feature ablations, and require holdout Brier improvement with
AUC ≥ 0.55 and ECE ≤ 0.05 before shadow promotion. Build session-specific
datasets rather than pooling all sessions.

## Phase 3B.3 / 3C — sessions, reachability and macro risk

Completed on 2026-11-03:

- Added `sessions.py`: DST-aware ASIA/LONDON/PREMARKET/NEW_YORK analytical
  windows, exchange RTH/OVERNIGHT/ETH, early-close dates and point-in-time
  `SessionSnapshot`.
- Added `research/session_dataset.py`: 147 rows / 49 days; next-same-session
  direction (BULL 72 / BEAR 69 / NEUTRAL 6) and range-state labels.
- Added `ml/session_model.py`: frequency, logistic and GBM direction models with
  multiclass Brier/log-loss/ECE/confusion, plus consolidation evaluation.
- Results: direction frequency log loss 0.8650 beats logistic 2.5272 and GBM
  1.3781; NEUTRAL is absent from the 30-row test split. Consolidation logistic
  Brier 0.1496 / AUC 0.8995 / ECE 0.1925 vs frequency 0.2333; **NO_PROMOTION**
  because ECE and sample size fail the gate.
- Added `price_levels/reachability.py`: empirical forward-MFE touch probability
  conditioned on ATR distance; explicitly not target-before-stop.
- Added `macro/calendar.py` and `data/macro/sample_events.json`: point-in-time
  event schema/store, `upcoming`/`recent`/`event_risk`, and critical-day states
  with `directional_bias=None`. The sample has null consensus; no authorized
  live calendar is wired.
- Added `forecast/bundle.py`: ASIA/LONDON/NY/NEXT_DAY research outlooks with
  expected range, levels, touch probabilities and `NO_TRADE`.
- Added `forecast/evaluation.py` and `scripts/evaluate_forecasts.py`: realized
  range, p50/p80/p90 coverage, target touches and explicit `NOT_MATURED`.
- Added `docs/PHASE3B3_FINDINGS.md`,
  `reports/phase3b3_session_models.md/json`,
  `reports/forecast_evaluation.json`.

Verification commands:

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python scripts/train_session_models.py
python -m nocturne forecast-bundle --instrument NQ
python -m nocturne evaluate-forecast --instrument NQ
python scripts/evaluate_forecasts.py
```

Blocked: authorized economic-calendar/news history, authentic tick/DOM/true
volume-at-price, CFE VX futures. Current V1 forecast is `NOT_MATURED`; no model
or forecast is promoted.

Next exact step: add an authorized point-in-time calendar adapter, expand the
session dataset beyond 60 days, and rerun session models with purged walk-forward
splits. Promotion gates: holdout Brier improvement, AUC ≥ 0.55, ECE ≤ 0.05 and
adequate sample size.

## Completed

Phase 0 — audit
- Read the full v2 package; audited the existing repo.
- Documented the gap analysis, decisions and status.

Phase 1 — contracts and data
- Pydantic event/level/prediction contracts.
- Instrument registry (NQ, MNQ, ES, MES, VX, ZN, ZB).
- DST-safe sessions, holidays, roll dates.
- Append-only JSONL event store with as-of replay.
- Yahoo bar adapter with provenance and incomplete-bar rejection.

Phase 2 — auction
- True trade-derived volume profile with POC/VAH/VAL, HVN/LVN and conservation.
- TPO profile, separate from volume.
- IB, opening range and VWAP.
- AMT balance/acceptance/value migration.

Phase 3 — strategies and backtest
- ORB/IB, VWAP pullback, VAH/VAL rejection.
- Bar backtester with costs, gap handling, stop-first ambiguity and a defined
  50/50 TP1/TP2 exit schedule.
- Real 60-day NQ 5m ORB result: 44 trades, 47.7% win, +$4,940, PF 1.1475,
  max drawdown $18,730, 41/44 timeouts. Development −$18,730 vs holdout
  +$23,670. Not promoted.

Phase 4 — models and API
- Triple-barrier labels and leak-safe features.
- Frequency, logistic and HistGradientBoosting baselines.
- Chronological walk-forward + Platt calibration.
- NQ result: frequency best (Brier 0.2474); logistic 0.2493; boosted 0.2488.
  `RESEARCH_ONLY`; no promotion.
- Model registry, append-only journal, read-only FastAPI.

Phase 5 — context
- ES/NQ relative state, beta, correlation, spread z-score.
- `^VIX` spot proxy (CFE VX blocked), ZN/ZB Yahoo proxies.
- Premarket state built from real 15m bars: 2026-11-03 NQ gap +0.46%,
  ES +0.05%, NQ led, VIX 21.41, ZN/ZB connected.

Phase 6 — order flow interfaces
- Typed trades/quotes, aggressor classification, CVD, footprint.
- Book reconstruction with sequence-gap invalidation.
- Data gate returns `UNAVAILABLE` without tick/quote history.

Phase 7 — knowledge
- Analyst thesis registry, separate from runtime inputs.

Phase 8 — safety
- Deterministic risk gates: stale data, low coverage, event lock, extreme
  volatility, expired signal, duplicate, negative EV -> `NO_TRADE`.
- Read-only API; no broker adapter or order endpoint.

## Verification

```bash
python -m pytest -q                 # 154 passed, 1 skipped (155 with native)
python -m nocturne audit
python -m nocturne train --instrument NQ
python -m nocturne forecast --instrument NQ
python -m nocturne context
python -m nocturne backtest --instrument NQ --days 60
python -m nocturne serve
```

## Blockers

- No true trade-by-price, tick, quote, DOM, or MBO history. Profile/order-flow
  code is tested with fixtures; live features are `DATA_BLOCKED`.
- No CFE VX futures history. `^VIX` spot is a labelled proxy.
- No licensed economic calendar redistribution; event gate is not wired to a
  live calendar.
- No C++ toolchain. Native source and parity contract exist, but no native
  module is built or claimed.

## Next exact step

1. Connect an authorized trade-by-price adapter and replace the bar
   approximation in the profile demo.
2. Add CFE VX front/back futures and a point-in-time calendar adapter.
3. Run the ORB/VWAP/value strategies across ES and NQ with a held-out final
   window and 2–4 tick cost stress.
4. Only after those gates: consider promotion, paper shadowing and a separate
   execution review.
