# Backend readiness — Phase 3M

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
  backtester remains unchanged.
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
- Action: `DATA_ACQUISITION_PHASE3M.md`. Cost stays null, not zero.

## Predictive validation — separate verdict

Only `ndx-range-v1` is shadow-active, still
`RESEARCH_VALIDATED_PENDING_SHADOW`. There is one legacy matured observation and
zero matured corrected-inference observations at this checkpoint. New index
logistic results are development diagnostics; NQ/ES direction, target-first,
survival, order flow and session models remain unvalidated or data-blocked.
All trading remains **NO_TRADE**. The full Phase 3M predictive acceptance scope
is not complete merely because all twelve job types have real handlers.
