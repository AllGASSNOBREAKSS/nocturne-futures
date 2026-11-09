# Backend readiness — Phase 4

## Phase 4 update (November 9, 2026)

Frontend now exists as a local desktop app (operator chose desktop over Vercel). It is a
loopback-only, single-user research tool: per-launch token, admin-only allow-listed mutations,
background jobs on the existing orchestrator, strict-JSON API, append-only session forecasts.
Engineering verification: 471 tests, Phase 3V parity, E2E through Electron, packaged exe.
Quantitative readiness is unchanged: no validated directional or trading model; Databento
history blocked pending key rotation and credit verification. NO_TRADE.


## Phase 3V update — NO_GO_FRONTEND (November 9, 2026 UTC)

Engineering: Databento metadata preflight verified and its range-key defect
fixed; free futures collection (1m/5m/60m/1d) with live-bar and monthly-downsample
defects fixed; deterministic, reproducible futures research and ranking; 451 tests.
Quantitative: authentic raw-contract, trade, quote and depth history still
absent by operator $0 policy. Validated research-only: compression and
large-range probability models (volatility persistence). Rejected: direction,
all target-before-stop geometries, all ranked signals; strategies insufficient.
No promotion; no readiness percentage.


## Phase 3U update — NO_GO_FRONTEND (November 9, 2026 UTC)

Evidence: `PHASE3U_FINDINGS.md`, `reports/phase3u_*.json`. Phase 3T gates below
still apply; 3U changes only the items listed here.

**Engineering.** Free-data ingestion added: six keyless official sources
collected (125,814 rows) through one polite client with rate limits,
retry/backoff, robots enforcement for crawling, checksummed archives and a
revision ledger. GDELT is blocked by rate limiting. Orchestrator gained
`FREE_DATA_COLLECTION` and content-addressed `FREE_DATA_EXPERIMENT`
(research lane, 900 s timeouts, single attempt); a real tick completed both in
71 s. Experiment peak memory 226 MB. 444 tests pass with native parity.

**Quantitative.** First end-to-end free-data historical study executed with
point-in-time joins: direction INCONCLUSIVE (every configuration worse than the
frequency baseline), free-feature range FAIL (base LightGBM range model beats
trailing quantiles). Forward evidence unchanged at 2 matured observations;
both pending forecasts still audit-blocked. Authentic futures data remains
`FUTURES_DATA_BLOCKED`. No model is promoted; no readiness percentage is claimed.


## Phase 3T acceptance — NO_GO_FRONTEND (November 8, 2026 UTC)

Evidence: `PHASE3T_FINDINGS.md`, `reports/phase3t_acceptance.json`, per-forecast
incident reports and current operational reports. Engineering and quantitative
gates are separate. The full pre-frontend conditions are **not met**; no 70% score
or predictive-accuracy claim is assigned. Earlier sections are historical.

### Engineering readiness

- **Automated orchestration — completed bounded functionality / partial deployment.**
  Five genuine shadow jobs and two reports updated; a concurrent research tick
  correctly reused existing work (zero new research jobs). Exclusive per-attempt
  receipts allow scoped completion with historical quarantine, retaining exit 1,
  IDs and BLOCKED job health. Actual failure/missing receipt does not take that
  path. `phase3t_assurance.json`, `tests/test_phase3t_integrity.py`. No independent
  always-on/long-soak or hard memory-isolation acceptance.
- **Historical backtesting — completed infrastructure / futures externally blocked.**
  Existing costs, replay, chronological validation and native parity contracts
  pass. No new authentic futures backtest was eligible or manufactured. License,
  sufficient contract coverage and real receipts are missing.
- **ML experimentation — completed infrastructure / new market fits not eligible.**
  Frozen model/cache/governance contracts pass; zero new market training jobs in
  phase. Purging/embargo and exposed-holdout restrictions preserved. No new
  independent data/hypothesis warrants repeating rejected experiments.
- **Continuous forward forecasting — partial, bounded operational proof.**
  Four genuine issues, no duplicates/misses. Existing November 9 issue returned
  idempotently while older audits blocked. Fixture tests demonstrate new eligible
  issuance independent of old quarantine; this is not a claim of a future actual
  deadline completion. Host must remain awake/interactively logged in.
- **Immutable outcome evaluation — partial / current incidents blocked.**
  Two existing outcomes independently replay against their archived research-grade
  observations. Both pending incidents have evidence-backed dispositions, original
  denominators/journal bytes preserved, but final independent OHLC is absent.
  November 6 is overdue and integrity-blocked; November 9 is additionally future.
  Classification is complete, clearance/evaluation is not. See `phase3t_incidents.json`.
- **API security — bounded controls verified / production acceptance partial.**
  Auth/roles/artifact restrictions, TLS, bounds, rate limits and secret-safe audit
  tests pass unchanged. No new HTTP mutation/acknowledgement/job route. External
  network/ACL/TLS lifecycle/security/load approval and independent paging remain.
- **Scheduler reliability — completed bounded lifecycle / partial availability.**
  Two exercised completions per deployed task preserve pythonw transport and all
  task definitions. Shadow exit 1 is quarantine, research exit 0; neither is claimed
  a crash, and overall health remains degraded. `phase3t_scheduler.json`. No account
  change, paid hosting, reboot/logoff or unattended soak was authorized/performed.
- **Recovery — partial.** Existing encrypted archive authenticated/restored/replayed
  765 files in 20.64s into a new isolated local directory, RESTORED_NOT_ACTIVATED.
  It is the November 6 three-issue recovery point, not current four-issue backup.
  `phase3t_encrypted_restore.json`. Independent destination/key custody, off-host
  restore and cutover/rollback remain **OFF_HOST_VERIFICATION_REQUIRED**. Proposed
  RPO 30m/RTO 60m are not achieved off-host SLOs.
- **Monitoring — partial.** Execution, issuance, provider freshness and outcome
  integrity are separate components. Four alerts remain open; acknowledgement
  retains OPEN and cannot waive/rescind a blocker. Exceptions/issuance failures
  cannot be concealed by older quarantine. Stale/malformed evidence is not health.
  Independent host-loss detection/paging and service/backup/audit capacity soak remain.
- **Python/C++ integration — completed at tested source.** Core `fcac56c`: 429 local
  and isolated tests pass, native parity included. TypeScript passes. Five CI jobs
  green at that commit, run 42465576451. 13,458 installed hashes and exact four-issue
  inference verify in reused locked environment. `phase3t_runtime.json`,
  `phase3t_tests.json`, `phase3t_ci.json`. Fix `6bd0f75` (no close-only fallback after
  full-bar reconciliation): 431 local and fresh-isolated tests pass; five CI jobs green
  in run 42466314331. Later report-only commits need their own CI result.

### Quantitative readiness

- **Authentic NQ/ES history — blocked / USER_ACTION_REQUIRED.** Credentials absent
  across checked scopes, zero licensed receipts. GLBX.MDP3 entitlement, raw-ID
  resolution, credits, price and approval unknown. No paid download. The existing
  bounded pilot/checklist remains `PHASE3S_FUTURES_PILOT.md`.
- **Training sample adequacy — blocked for futures.** No suitable independent
  contract history/events; a one-session plumbing pilot alone cannot qualify ML.
- **Bullish/bearish discrimination — blocked.** No new independently validated
  futures directional finding. Cash-session range forecasts are not NQ direction.
- **Consolidation forecasting — blocked.** Infrastructure is not a calibrated
  futures consolidation model; independent labels/observations are absent.
- **Significant levels — partial feature plumbing / predictive qualification blocked.**
  Authentic trade/volume-at-price, bid/ask and justified depth coverage plus independent
  level/path evaluation are missing. Daily bars never substitute for order flow.
- **Target-before-stop calibration — blocked.** 100/200/350/500-point NQ destination
  probabilities remain null/unsupported. Adequate authentic paths, realistic costs,
  tie/ambiguity policy, horizon selection, separate calibration and independent
  holdout are required; no attractive targets were forced.
- **Independent strategy validation — blocked.** No untouched authentic futures
  holdout/events. Old exposed index/proxy diagnostics remain diagnostic only.
- **Forward performance evidence — partial / insufficient.** Four cash-index range
  issues, two verified outcomes (one per cohort), two quarantined/pending. This
  cannot establish reliable calibration, directional skill or executable edge.

**Decision: NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.** Remaining source-finality,
licensed-data, independent deployment/recovery/security/monitoring and statistical
evidence gates require real inputs/authorization, not redundant infrastructure.

## Phase 3S acceptance — NO_GO_FRONTEND (November 8, 2026 UTC)

Evidence: `PHASE3S_FINDINGS.md`, `PHASE3S_SECURITY_DEPLOYMENT.md`,
`reports/phase3s_acceptance.json`. Engineering controls improved; the complete
pre-frontend acceptance criteria are **not met**. No numerical 70% claim is assigned.

### Engineering gates

- **Scheduler reliability — PARTIAL.** November 6 repeated zero-exit receipts are
  retained; November 8 shadow exits 1 because source audit gates correctly block,
  research exits 0. Both complete lifecycle journaling. Four alerts/core degraded.
  `phase3s_scheduler.json`, `phase3s_scheduler_current.json`. Interactive/awake-host
  only; unattended startup profiles are prepared/dry-run, not activated or soaked.
- **Automated backtesting — COMPLETED, development scope.** Existing chronological
  cost-aware research infrastructure/tests remain reproducible; no new authentic
  futures results. `tests/test_backtest_regression.py`, `tests/test_daily_experiment.py`.
- **ML training — COMPLETED, infrastructure scope.** Existing purging/embargo,
  frozen identity/cache and governance tests pass. Zero new market fits and no
  repeated tuning on exposed holdouts. Model quality is not an engineering pass.
- **Forward testing — PARTIAL / AUDIT_BLOCKED.** Four genuine issues, two verified
  historical outcomes, two pending; pending reference bars revised. November 6
  passed time eligibility, not integrity eligibility. Unapplied investigations are
  `phase3s_revision_nov06.json` and `phase3s_revision_nov09.json`. No forced evaluation.
- **API security — COMPLETED bounded controls / PARTIAL deployment approval.**
  Tested reader/admin auth, fail-closed artifact access/audits, minimal liveness,
  host/input/request/rate limits and real isolated verified TLS. No mutation routes.
  Single-process profile only; external security/load/ACL/TLS lifecycle review and
  production configuration remain. `tests/test_api_security.py`, `tests/test_tls_deployment.py`.
- **Data integrity — PARTIAL overall.** Frozen model, original journal prefixes,
  archived outcomes and exact issued-row replay verify. Current source-reference
  discrepancies remain detected/blocked, not silently normalized. Historical
  research-grade outcomes are not exchange-finality evidence. `phase3s_acceptance.json`,
  `phase3s_runtime.json`, `phase3j_operations.json`.
- **Deployment reproducibility — COMPLETED isolated Windows scope / PARTIAL host
  acceptance.** Fresh offline security environment, 58 reviewed wheel hashes,
  13,458 installed-file hashes, fresh C++20 and exact original inference verify.
  No live path migration, independent host cutover, reboot/logoff or hard memory
  isolation evidence. `phase3s_dependency_lock.json`, `phase3s_runtime.json`.
- **Recovery — PARTIAL.** AES-GCM package authentication, secret exclusions,
  original manifest, model/source/journal/SQLite and cached-diagnostic replay work
  on a real 765-file November 6 snapshot. Restore/replay 23.70s, not full RTO.
  OFF_HOST_VERIFICATION_REQUIRED; no authorized independent destination/key custody.
  Proposed RPO 30m/RTO 60m remain objectives, not achieved SLOs.
- **Monitoring — PARTIAL.** Durable alerts/lifecycle journals report actual failures;
  four alerts open. No independent paging, always-on backup/audit-capacity monitoring
  or long soak. Do not equate fail-closed behavior with healthy operation.
- **Python/C++ CI — COMPLETED at recorded implementation.** 408 local and isolated
  tests pass including native parity; final full isolated source is `c5de881`,
  with 13,458 installed hashes and all four issued-row replays verified in
  `phase3s_runtime_final.json`. TypeScript passes November 8. All five CI jobs are
  green at `c5de881`, run 42464277742 (`phase3s_ci.json`). Later receipt/documentation
  commits need separately checked CI; no Python/C++ or workflow changes follow.

### Quantitative intelligence gates

- **Genuine futures data — BLOCKED / USER_ACTION_REQUIRED.** Zero licensed NQ/ES
  receipts. GLBX.MDP3 credentials/entitlements/raw IDs/quote/approval unverified;
  no paid consumption. `PHASE3S_FUTURES_PILOT.md`, `phase3s_data_access.json`.
- **Historical coverage — PARTIAL context / BLOCKED futures.** Cash-index and
  continuous-proxy archives are not raw-contract futures history; a one-session
  pilot cannot establish adequate independent coverage.
- **Market direction prediction — BLOCKED.** No independently qualified futures
  directional model or new authentic event/path evidence.
- **Consolidation prediction — BLOCKED.** No sufficient independent futures
  observations or validated calibrated model.
- **Significant price levels — PARTIAL feature infrastructure / BLOCKED predictive
  qualification.** Genuine volume-at-price/depth paths and independent level-hit
  evaluation remain absent; no synthetic order-flow claims.
- **Target-before-stop calibration — BLOCKED.** Adequate authentic paths, realistic
  costs, ambiguity handling, separate calibration and independent tests required.
  Unsupported 200–500-point target probabilities remain null.
- **Independent validation — BLOCKED.** No new untouched futures holdout; exposed
  historical holdouts remain diagnostic and cannot be reused for selection.
- **Genuine forward observations — PARTIAL / insufficient.** Four issued cash-index
  range forecasts; two verified outcomes (one per inference cohort), two pending.
  This does not establish reliable coverage, direction skill or trading accuracy.

**Decision: NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.** No paid resources/public
deployment or broker execution activated. Remaining independent engineering and
quantitative gates cannot be replaced by more tests or an arbitrary completion score.
Earlier sections below are historical checkpoints, not current operational health.

## Phase 3R acceptance — NO-GO frontend

Evidence: `PHASE3R_FINDINGS.md`, `PHASE3R_REPRODUCIBILITY.md`,
`reports/phase3r_acceptance.json`. No percentage or predictive-readiness claim.

### Engineering

- **Dependency reproducibility: verified bounded Windows 3.14 scope.** Fifty-five
  exact wheel hashes checked against actual PyPI metadata, offline hash-required
  bootstrap and 13,290 installed RECORD file hashes. Source/Python/package/native
  manifests: `phase3r_dependency_lock.json`, `phase3r_runtime.json`. Trusted base
  tooling/local metadata and cross-platform limitations remain explicit.
- **Frozen inference: verified exact issued-row replay.** Three original cases,
  legacy/corrected cohorts separate, exact float-hex comparison. Loader rejects
  six-library numerical drift before pickle loading/inference. Artifact and old
  journal bytes unchanged. `tests/test_environment_integrity.py`,
  `phase3r_runtime.json`, `phase3r_acceptance.json`.
- **Bootstrap/native integration: verified fresh environment, same host.** New
  offline venv/independent clone/fresh C++20 build; final local and isolated suites
  each pass 384 tests including native parity. Five CI jobs pass at `3a88a5d`,
  including Windows hash-locked bootstrap. `reports/phase3r_ci.json`.
- **Scheduling/recovery: verified bounded completions, partial deployment.** Real
  01:47 backup contention returned 75, retained in `phase3r_backup_collision.json`.
  Capture admission and bounded maintenance wait address that collision without
  masking failures; subsequent two completions per task have complete zero-exit
  receipts (`phase3r_scheduler.json`). No task settings/principals/triggers changed.
  Interactive/awake-host, reboot/logoff/soak and independent monitoring limits remain.
- **Private recovery: verified local proof, off-host blocked.** Coherent SQLite,
  archives, model and outcome replay verifies; original local restore/replay took
  13.70 seconds. `phase3r_recovery_*.json`. Proposed RPO 30 minutes/RTO 60 minutes
  are not achieved off-host SLOs. Authorized encrypted off-host destination,
  independent key custody, separate-host restore and cutover/rollback remain absent.
- **Research orchestration: verified eligible scope.** Five actual shadow jobs and
  reporting executed; unchanged research tick reused existing validation. All 12
  job types inventoried without claiming each ran anew (`phase3r_assurance.json`).
  No exhausted directional fit or exposed holdout was repeated.
- **API security: narrow input fix verified, deployment partial.** File-backed
  query inputs reject path escapes/overlong identifiers; no mutating routes.
  `tests/test_api.py`. Authentication/TLS/rate limiting/load review, external access
  controls, independent paging and hard memory isolation remain missing. Default
  loopback binding is not approval to expose the unauthenticated API publicly.

### Quantitative

- **Authentic NQ/ES data: USER_ACTION_REQUIRED.** Zero licensed receipts; keys and
  real entitlement/quote/approval absent. `phase3r_data_access.json`; single exact
  acquisition checklist: `PHASE3P_DATA_ACCESS.md`. No paid consumption or adapter
  rebuild. A price estimate is unknown, not zero.
- **Independent direction/strategy/target calibration: blocked.** No new authentic
  futures backtest/model. Old fixed index diagnostics remain negative and are only
  replayed for reproducibility. Order flow and 200–500-point target probabilities
  require adequate authentic paths/events and realistic costs; unsupported values
  stay null. `PHASE3R_FINDINGS.md`, `phase3r_assurance.json`.
- **Forward sample adequacy: insufficient.** Three issued, two research-grade
  matured, one pending; one matured per cohort. November 6 remains ineligible until
  November 7 00:00 UTC plus original gates. Two samples do not establish reliable
  calibration or prediction accuracy. `phase3i_forward.json`,
  `phase3l_forward_audit.json`; no exchange-finality claim.

**Decision: NO-GO frontend; NO_PROMOTION / NO_TRADE.** Remaining gates require
independent deployment/durability/security/availability evidence and authentic
independent quantitative observations, not more test-count inflation. Earlier
sections below are historical checkpoints.

## Phase 3Q acceptance decision — NO-GO frontend

No completion percentage is assigned. Engineering evidence improved; independent
quantitative acceptance remains blocked. Current evidence:
`reports/phase3q_acceptance.json`, `PHASE3Q_FINDINGS.md`, `PHASE3Q_DEPLOYMENT.md`.

### Engineering gates

- **Orchestration — verified bounded scope.** Fresh SQLite/venv executed actual
  nine-source archival validation, without training/repeating old experiments:
  `reports/phase3q_clean_validation.json`; `tests/test_research_orchestrator.py`.
- **Scheduled operation — verified repeated local completions, partial deployment.**
  Six genuine scheduled zero exits with complete launcher/stage evidence after
  console-free transport: `reports/phase3q_scheduler.json`. Hidden-window-only
  mitigation failed (`phase3q_hidden_experiment.json`). Old control-event sender
  is unconfirmed, not blamed on a particular user/policy. Task actions alone changed;
  principals/settings/triggers match (`phase3q_task_action_changes.json`). Reboot,
  logoff, approved service-account mode, long soak and 24/7 operation remain untested.
- **Backtesting/ML validation — verified development interfaces only.** Existing
  tests plus exact old index-diagnostic replay and six cached model hashes:
  `reports/phase3q_recovery_check.json`; `tests/test_daily_experiment.py`. No new
  independent model/strategy finding or promotion is established.
- **Forward forecasting/evaluation — verified research-grade scope.** Three issued,
  two verified matured, one pending; corrected cohort has one matured outcome.
  `reports/phase3i_forward.json`; `reports/phase3l_forward_audit.json`.
- **Registry/governance — verified preservation/no-promotion.** Exact old journal
  prefixes and frozen model hash in `reports/phase3q_acceptance.json`;
  `tests/test_model_governance.py`, `tests/test_promotion_evidence.py`.
- **Native/dependencies — verified fresh-environment scope.** New C++20 build and
  362 passing tests/no skips in isolated pinned venv; native/package paths checked:
  `reports/phase3q_environment.json`, `requirements/windows-py314.lock.txt`.
  Newer NumPy/pandas passed fixtures but blocked real proof replay; original pins
  restore exact replay (`phase3q_dependency_incident.json`). Do not relax audits.
- **Clean-host/recovery — partial.** Independent clone/venv/native build plus
  654-file private proof replay works, but still on the same Windows host.
  `reports/phase3q_recovery_*.json`; `PHASE3Q_DEPLOYMENT.md`. Separate OS/host,
  authorized off-host durability/encryption, cutover/rollback and historical
  absolute-path resumption remain unverified. No public upload occurred.
- **API/security/monitoring — partial.** Read-only API regression tests pass;
  `tests/test_api.py`, `tests/test_shadow_operations.py`. Deployment authentication,
  TLS/network exposure/security/load review, independent paging, hard process-memory
  isolation and accepted availability design remain missing.

### Quantitative gates

- **Authentic futures history — USER_ACTION_REQUIRED.** Zero licensed NQ/ES rows;
  no configured credentials, verified entitlement/credits, actual quote or approval.
  `reports/phase3q_data_access.json`; the single operator checklist remains
  `PHASE3P_DATA_ACCESS.md`. Price is unknown, not zero. No metered request occurred.
- **Independent strategy/direction/consolidation evidence — blocked.** No authentic
  futures pipeline result; old 6,036-observation index diagnostics are reproducibility
  evidence only and remain negative after hypothetical 2 bp. Existing logistic
  results are development-only. See `PHASE3Q_FINDINGS.md` and `PHASE3N_DATA_DECISION.md`.
- **Calibrated target-first probabilities — blocked.** Genuine contract paths,
  adequate events, independent evaluation, realistic costs and calibration are
  absent. 200–500-point targets are not inferred from daily ranges. Unsupported
  probabilities stay null; `tests/test_target_survival.py` is engineering evidence,
  not market validation.
- **Forward evidence — insufficient.** Two research-grade matured outcomes across
  two different inference cohorts, one each. November 5 missed all three range
  quantiles; no accuracy/calibration claim follows from this sample. Original
  denominators/observations unchanged; exchange finality remains unconfirmed.
  `reports/phase3i_forward.json`, `reports/phase3l_forward_audit.json`.

**Decision: NO-GO frontend; NO_PROMOTION / NO_TRADE.** Close the explicitly missing
deployment/security/durability gates and obtain genuinely independent quantitative
evidence before revisiting acceptance. Earlier sections below are historical.

## Phase 3P evidence update

**Pre-frontend gate NOT PASSED. No percentage assigned.** See
`PHASE3P_FINDINGS.md`, `PHASE3P_DATA_ACCESS.md` and `reports/phase3p_evidence.json`.

Engineering: 355 local tests including native parity, TypeScript passed; bounded
private evidence snapshot and separate-location SQLite/source/model proof replay
verified on 547 files (210,599,711 bytes). Two fixed authentic index diagnostics
reproduce exactly; six cached challenger files retain their hashes. This is
same-host recovery using the installed environment, not clean-host/off-host restore.

Quantitative: zero licensed futures rows; two issued, one verified legacy matured,
one pending corrected forecast before November 6 00:00 UTC. No new models, unseen
evaluations, target probabilities or predictive claims. Both fixed index diagnostics
remain negative at hypothetical 2 bp; old ML findings remain development-only.

Operational qualification: direct shadow runner succeeds, but both Task Scheduler
launches currently return 0xC000013A (interrupted). **Scheduled operation DEGRADED**,
even while core reports are healthy. Root cause and successful complete scheduled
stage receipts must be established without weakening host security. Interactive
awake/logged-in limitation remains; task definitions/principals unchanged.

Outstanding measurable gates: authorized receipt-validated NQ/ES pilot; independent
multi-regime futures/event/calibration evidence and adequate corrected forward
samples; restored scheduled completion; clean-host and off-host recovery; accepted
availability/independent-monitoring design; process-memory isolation; API deployment
authentication/security/load review. Tests do not satisfy those external gates.

The following Phase 3O/earlier sections retain historical evidence, not current
scheduler or quantitative approval.

## Phase 3O evidence update and pre-frontend gates

**Engineering:** recovered source audit via exact archived issuance replay and a
separate full-bar-bound proof; real cycle/monitor recovery; component-level health;
correct blocked/disabled job semantics; seven-job isolated subprocess integration.
348 local tests including native parity, TypeScript, plus branch CI verification.
No new scheduler, data adapter or market model was created.

**Quantitative:** still zero licensed futures rows, one legacy matured outcome and
zero corrected-inference matured outcomes. November 5 remains pending until the
November 6 availability bound. The source discrepancy is reconciled as issued,
not confirmed exchange truth. No new direction/target/survival validation exists.
These are separate dimensions, not an accuracy or completion percentage.

Before frontend development, require an explicit gate review of:
1. Authorized NQ/ES pilot received and independently reproducible from raw receipts
   through the existing engine, with calendar/availability limitations resolved.
   **BLOCKED: credentials/quote/user approval.**
2. Source-revision/outage recovery, worker failure/restart, deadline and deterministic
   end-to-end CI contracts. **VERIFIED in bounded tests and current source recovery**;
   host reboot/logout/long-duration soak remain unverified.
3. Consistent private snapshot + journal + SQLite backup and clean-host restore
   with intact hash proof. **PARTIAL: local evidence exists, off-host restore absent.**
4. Authorized deployment model and independent monitoring: either an explicitly
   accepted awake/logged-in limitation or verified unattended operation/paging.
   **PARTIAL: interactive tasks only; no 24/7 claim.**
5. Versioned read-only API/report contract, deployment authentication/security and
   error/freshness behavior suitable for a client. **PARTIAL: regression-tested API;
   external deployment/security/load review remains.**
6. Model-governance review that keeps historical diagnostics, live forward samples,
   research challengers and null unsupported probabilities separate. **VERIFIED
   no-promotion scope**, not predictive or trading approval. Independent evaluation,
   futures sample adequacy and target calibration remain **BLOCKED** quantitatively.

Frontend work has not begun; this gate review has not passed. No arbitrary 70%
claim is made. See `PHASE3O_FINDINGS.md`, `PHASE3O_DATA_ACCESS.md` and
`reports/phase3o_operations.{json,md}` for current evidence. The sections below
retain earlier milestones as historical scope, not a substitute for this update.

## Phase 3N evidence update

No overall percentage is assigned. Authentic futures readiness remains **blocked**,
not improved statistically by the new engineering. See `PHASE3N_DATA_DECISION.md`
and `reports/phase3n_futures_access.json` for the single acquisition decision.

- Data reliability/provider access: documented free metadata preflight, raw-ID
  resolution, range/condition/count/size/cost checks and request-bound explicit
  approval now precede any metered request. Reservations prevent blind charged
  retries; rejected bodies/partial prefixes remain archived. Byte caps are not
  hard process-memory or final-invoice limits. Tests: `test_databento_access.py`.
- Historical backtesting/price levels: verified receipts now connect to the
  existing ORB/bar-VWAP backtester and ambiguity-aware target labels. Tests run
  the full path on isolated fixtures; actual NQ and ES jobs still return BLOCKED
  with zero licensed rows. No real strategy, directional or survival result exists.
  Cashflow-v2 corrects legacy double entry-slippage/exit-fee counting with analytic
  tests; old reports retain legacy-v1. Real execution and intrabar excursion
  assumptions still require validation; simulated results are not an execution edge.
- Scheduled operation: latest research result 0; latest shadow result 1 from an
  appropriately blocked source audit. The pending forecast's issued reference
  28437.166015625 differs from current Yahoo 28437.169921875; alerts remain open.
  research now checks both explicit pilot contracts without automatically
  downloading data. Actual host restart/logout and off-host service availability
  remain unverified; no credentials or security settings were changed.
- Forward state: still two issued, one verified legacy matured and one pending;
  November 5 cannot be evaluated before November 6 00:00 UTC. Forecast/model bytes
  preserved. Pending forecast is AUDIT_BLOCKED until its new reference revision
  is deliberately investigated; first outcome verification does not clear it.
  No new model fit or promotion in Phase 3N.
- Regression evidence: **342 local tests including native parity**, TypeScript
  typecheck; branch CI must also be verified after push. New tests cover approval,
  budget, metadata/entitlement errors, consumed retries, timestamp/volume/ID
  integrity, sparse grids, DST, engine integration and read-only access reporting.
  Default research does not rerun old index diagnostics; unchanged futures inputs/
  code share one job identity across dates and manual/scheduled entry points.

The fourteen-category framework below retains its stated narrow scope and missing
requirements; source quality does not become independently certified PIT history.

This is an evidence checklist, not a subjective completion percentage. Review
engineering readiness separately from predictive validity. No claim that the
backend is 70% complete, ready for frontend integration, or eligible to trade is
made from this checklist. A partial category is not counted as complete merely
because an interface exists.

## Measurement framework

Each category needs (1) implemented code, (2) a passing reproducible verification,
and (3) required operational/data evidence. **Verified scope** means these exist
for the stated narrow scope; **partial** means a material requirement remains;
**blocked** means required external evidence is absent. Reassess after the
licensed pilot, clean-host recovery and unattended deployment, rather than
assigning arbitrary weights to meet a target number.

### 1. Data pipeline reliability — partial
- Implemented: authorized public adapters, retries, immutable archives, refresh
  guards, raw-contract receipts and source-revision reconciliation.
- Tests: `test_market_snapshots.py`, `test_phase3e_providers.py`,
  `test_daily_experiment.py::test_receipt_hash_mismatch_blocks_before_research`.
- Missing: licensed pilot, authoritative finality/latency, feed SLA and off-host backup.

### 2. Historical dataset integrity — partial
- Verified: nine daily raw/normalized receipts; NDX 10,353 rows spanning 41.09
  years, S&P 500 24,828 rows; distinct ETFs and continuous proxies remain separate.
- Tests: `test_history_manifests.py`, source replay in `daily_experiment.py`.
- Missing: original publication vintages, contract-roll evidence and licensed
  intraday history. A long retrospective series is not certified historical PIT.

### 3. Automated backtesting — partial
- Executed: two fixed index-context diagnostics, 6,036 observations each,
  2000–2023; cost sensitivity and yearly results recorded. Existing futures
  engine remains in use with explicit legacy-v1 and cashflow-v2 accounting.
- Tests: `test_backtest.py`, `test_backtest_regression.py`, `test_daily_experiment.py`.
- Missing: authentic NQ/ES session strategy runs with trade/stop/timeout/MFE/MAE
  and futures costs; the corresponding job reports `BLOCKED`, not fake zero trades.

### 4. Walk-forward validation — verified development scope
- Implemented: existing grouped chronological purging and elapsed-time embargo,
  separate calibration, fixed fold protocol; 2024+ not scored in the new jobs.
- Tests: `test_phase3d_validation.py`, `test_daily_experiment.py`.
- Missing for model validation: genuinely independent unseen evaluation and
  sufficient event/regime coverage. Previously studied eras are diagnostics only.

### 5. ML experiment reproducibility — verified bounded scope
- Executed: fixed logistic/frequency comparisons for two indices, three folds
  and 750 development test rows each; model/data/source digests and saved code.
- Tests: deterministic refits and corruption/cache rejection in
  `test_daily_experiment.py`. Identical dataset/protocol/code identities reuse
  saved artifacts and metrics, not repeated model selection.
- Missing: clean-host environment/artifact restoration and broader independently
  justified feature/model experiments. No neural model or automatic promotion.

### 6. Price-level research — partial
- Existing: trade profiles, TPO, auction levels, VWAP, target labels, corrected AJ.
- Tests: `test_volume_profile.py`, `test_tpo.py`, `test_contract_replay.py`,
  `test_target_survival.py`; no synthetic test data enters live journals.
- Missing: authentic trade/quote/depth history and independent target calibration.

### 7. Forward prediction infrastructure — verified NDX range scope
- Existing model remains frozen and shadow-active; original forecasts unchanged.
- Tests: `test_shadow_service.py`, `test_market_snapshots.py`, native parity.
- Missing: validated NQ/ES/session/directional/target shadow candidates. Range is
  not a trade signal; no broader forecasting capability is implied.

### 8. Automatic outcome evaluation — verified research-grade scope
- Observed: one real matured outcome; November 5 forecast still pending. Existing
  scheduler and orchestrator both reuse idempotent append-only evaluation/audits.
- Tests: `test_outcome_audit.py`, `test_shadow_task_runner.py`.
- Missing: exchange-grade independent corroboration and enough genuine forward
  samples. Never reinterpret one observation as calibration accuracy.

### 9. Model registry and governance — verified no-promotion scope
- Existing: frozen checksums, research/shadow distinction, null unvalidated outputs.
  New challengers live in private experiment storage, never the active registry.
- Tests: `test_model_governance.py`, `test_promotion_evidence.py`,
  `test_research_orchestrator.py::test_dependencies_must_exist_and_cannot_tie_training_to_inference`.
- Missing: independently satisfied promotion evidence; trading authorization remains absent.

### 10. Scheduled operation and recovery — partial
- Deployed: existing 30-minute shadow task plus separate six-hour research task,
  both interactive; observed successful exits. SQLite jobs, OS lane locks,
  retry/backoff, restart reconciliation, child watchdog, budgets and lower
  research priority are implemented.
- Tests: `test_research_orchestrator.py`, `test_shadow_operations.py`,
  `test_shadow_task_runner.py`; task-definition CI dry runs.
- Missing: authorized logout-independent deployment, reboot/logout verification,
  hard memory/cgroup/job-object isolation and off-host availability checks.

### 11. API stability — partial
- Read-only API preserved; `/v1/research/status` exposes a timestamped snapshot
  with freshness, not job execution. No order or mutation endpoint added.
- Tests: `test_api.py`; TypeScript typecheck remains green locally.
- Missing: deployment auth, external API compatibility/load/security audit and SLOs.

### 12. Python/C++ coverage — verified regression scope
- Baseline reproduced: 291 tests including native parity. Phase 3M adds runner,
  recovery, timeout, cache, reproducibility, causal-feature and read-only API tests.
- Commands: `$env:PYTHONPATH='D:\nocturne-futures\native\build'; python -m pytest -o addopts=''`
  and `npm run typecheck` in `ts/`. Check this branch's CI, not only the old run.
- Missing: quantified branch coverage, extended stress/soak and multi-host tests.
  Passing tests are not statistical validation.

### 13. Monitoring and reporting — partial
- Implemented: immutable attempt reports/logs/events, historical experiment records,
  JSON/Markdown snapshots, failure reasons, forward audits and existing alerts.
- Tests: `test_shadow_alerts.py`, `test_research_orchestrator.py`.
- Missing: off-host paging, retention/backup policy and long-duration reliability evidence.

### 14. Provider readiness — blocked for futures research
- Immediately usable: verified retrospective daily context. Prior successful
  FRED/BLS probes do not constitute current PIT event feeds.
- Missing: Databento GLBX.MDP3 credential, exchange entitlement and authorized
  pilot cost quote; also actual trades/quotes/depth, VX and event/consensus history.
- Action: `PHASE3N_DATA_DECISION.md`. Cost stays null, not zero.

## Predictive validation — separate verdict

Only `ndx-range-v1` is shadow-active, still
`RESEARCH_VALIDATED_PENDING_SHADOW`. There is one legacy matured observation and
zero matured corrected-inference observations at this checkpoint. New index
logistic results are development diagnostics; NQ/ES direction, target-first,
survival, order flow and session models remain unvalidated or data-blocked.
All trading remains **NO_TRADE**. The full Phase 3M predictive acceptance scope
is not complete merely because all twelve job types have real handlers.
