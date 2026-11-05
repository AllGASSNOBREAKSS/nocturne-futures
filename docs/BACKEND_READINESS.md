# Backend readiness — Phase 3P

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
