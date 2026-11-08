# Phase 3S — backend security and operational evidence

Branch `feat/phase3s`, base `504a168`. Work began November 6; resumed November 8,
2026 UTC. **NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.** No readiness percentage
is defensible; the agreed pre-frontend acceptance gates are not all met.

## Implemented and verified

- Protected API routes use distinct reader/admin bearer credentials loaded from
  private files. No credentials means no protected data access. Admin is a read
  permission, not authority to execute jobs, mutate artifacts or promote models.
- Minimal public liveness is separated from administrator API readiness. Detailed
  research, operational and data-audit views require administrator access. HTTP
  docs/schema endpoints are disabled; direct Python service interfaces remain.
- Single-process peer/principal rate limits, bounded tracking, host allowlisting,
  header/path/query/body bounds, observed chunked-size checks and body timeout are
  tested. Existing instrument/session validation remains. Proxy headers are not
  trusted. CLI binding defaults to loopback; remote binding explicitly requires
  authentication, TLS and an operator flag. No public listener was started.
- Audit records exclude raw paths, query/body/header/secret values and require a
  successful fsync before releasing protected responses. The bounded private audit
  log fails closed at capacity; operator archival/rotation is required. This is
  not an independent security review or external load/DDoS certification.
- Reproducible local TLS deployment accepts certificate/key files. A real isolated
  loopback listener verifies certificate/hostname, TLS 1.2/1.3, authenticated reads,
  anonymous rejection, security headers and plaintext rejection. A first test left
  server shutdown waiting for connections; a bounded graceful-shutdown timeout fixed
  this. No system trust-store changes or production certificates were made.
- Research task installation now supports explicit Password/startup mode, preserving
  existing pythonw transport and no-overwrite behavior. Both unattended installers
  pass WhatIf without registration or credentials. Local/future always-on profiles
  start nothing. Live tasks retain Interactive/Limited principals and settings.
- AES-256-GCM packaging binds schema/header and snapshot manifest; authentication
  finishes before extraction. Byte/member limits, traversal/link/duplicate rejection,
  manifest checks, known-secret/path exclusions and wrong-key/tamper tests pass.
  Keys stay outside archives/repository; no secrets were printed or uploaded.
- New security dependency profile adds cryptography/cffi/pycparser to the existing
  immutable numerical profile: **58 wheels / 145,253,614 bytes**, checked against
  actual PyPI metadata. Fresh offline clone/venv/native C++20 build verifies **13,458
  installed file hashes** and all three original issued-row quantiles exactly.
  Old numerical constraints, model binary and journal prefixes remain unchanged.

Operational commands and limitations: `PHASE3S_SECURITY_DEPLOYMENT.md`.
Architecture: `ARCHITECTURE_PHASE3S.md`; governance: `architecture/model_validation.md`.

## Tests, CI and recovery

At `61878d5`, local and clean isolated suites pass **406 tests** including native
parity, with no isolated skips/failures/errors. TypeScript passes. All five CI jobs
pass at that exact commit in run **42153192576**. The earlier implementation
`b722033` also passed CI. Phase 3R documentation HEAD `504a168` independently passed
run 42148418888; prior green implementation evidence was not misattributed to HEAD.
Later report/documentation commits need their own CI result. Evidence:
`reports/phase3s_tests.json`, `phase3s_ci.json`, `phase3s_runtime.json`.

On November 8, the old temporary drill venv's Python executable was absent, so a
latest-source rerun could not start. Cause is unknown; prior test XML and restored
evidence remain. The interruption is retained in
`phase3s_isolated_rerun_interruption.json`; a separate fresh clone/venv at
`C:/Users/huzai/AppData/Local/Temp/opencode/nocturne-phase3s-final/` replaces it for
new testing, without deleting the earlier directory. Temporary artifacts are not
durable backups.

The replacement environment completed **408 tests, zero failures/errors/skips** at
`c5de881` (95.65s XML duration), with fresh native build. Local suite also passed
408 (91.28s); subsequent acceptance-helper changes have targeted coverage and are
included in the final complete isolated suite. November 8 TypeScript passes.
Final runtime evidence in `phase3s_runtime_final.json` verifies 13,458 installed-file
hashes and **all four issued forecasts** exactly. This supersedes the original
three-case replay count, not the frozen model or original issuance evidence. CI
results remain separately commit-bound in `phase3s_ci.json`; source `b75ee44` also
passed all five jobs, run 42464001630.

Final check confirms **all five CI jobs successful at `c5de881`**, run
**42464277742**. Subsequent receipt/documentation-only commits are not implicitly
covered by this run; no Python/C++ or workflow change follows the tested source.

Real November 6 snapshot: **765 files / 239,693,198 bytes**, manifest
`b75aaffc57d18a8b0bd2781783253c5dc5fe44b5c5b4a537f12e7ed89ae5960f`.
Capture checked real task deadlines and completed in 14.14s. Local encrypted
packaging took 13.02s, producing 240,445,663 ciphertext bytes. Fresh isolated
environment authenticated/restored/replayed that evidence in **23.70s**, including
three issued forecasts/two outcomes, archived source proofs, six cached challenger
hashes and two old negative index diagnostics. Zero network requests/new fitting
were used for the restore proof; restored services were not activated.

This is a November 6 recovery point, not a backup of all November 8 appended state.
No authorized independent destination exists. **OFF_HOST_VERIFICATION_REQUIRED**.
Proposed RPO 30m/RTO 60m are not achieved off-host SLOs. Local timings exclude host
provisioning, transfer, key delivery, scheduled-service cutover and rollback.
Same-host temporary demo-key storage does not establish independent key custody.

## November 8 live-state discovery — do not conceal audit failures

November 6 exercise retained two complete zero-exit receipts per task in
`phase3s_scheduler.json`. On resumption the clock was November 8 08:33 UTC, and the
existing scheduler had appended a fourth genuine forecast, targeting November 9.
The source provider subsequently revised both pending forecasts' reference bars.

- November 6 forecast `291aac9c9d893a888609aafd`: issued reference
  **26629.80859375**, current **26629.810546875**. Original forecast SHA remains
  `8344c61bcd20afe22003ef0f09f200308182d86694428044314afd560e9f6156`.
- November 9 forecast `cd26071237a957cd7a874933`: issued reference
  **26989.9921875**, current **26989.990234375**.
- Full bars also changed, notably provider volume. Existing reconciliation tooling
  exactly reproduces issuance features and classifies both as provider revisions;
  this is not independent exchange confirmation. FRED reference access failed and
  Nasdaq returned unavailable/404. Investigation reports are separate, **unapplied**:
  `phase3s_revision_nov06.json`, `phase3s_revision_nov09.json`. Original forecast and
  outcome bytes were unchanged by investigation. `--report` now avoids overwriting
  one investigation report with the next. No automatic reconciliation is enabled.
- November 6 has passed its time bound but **cannot be recorded as a matured
  evaluated outcome while integrity gates remain blocked**. November 9 is also
  still time-pending. There are **4 issued / 2 verified matured / 2 pending / 0
  missed**, with one verified outcome in each inference cohort. The forward report's
  two failures mean forecast audit failures, not two fabricated trading losses.
- Current shadow task completes its lifecycle with **exit 1 / AUDIT_BLOCKED**;
  current research task exits **0**. Four operational alerts remain open and core
  health is degraded. Fail-closed behavior is not a healthy-operation claim.
  Current scheduler receipts: `phase3s_scheduler_current.json`; operations:
  `phase3j_operations.json`, `phase3o_operations.json`.

Resolution requires deliberate evidence-bound review under the existing research
source contract, then full audit and maturity/evaluation gates. Never rescale
denominators, rewrite forecasts, loosen tolerances or erase alerts. Later source
revisions invalidate full-bar-bound proofs and require new deliberate review.

## Authentic futures pilot and remaining actions

Provider credentials were absent across process/user/machine scopes at the checked
preflight; actual GLBX.MDP3 entitlements, credits, raw IDs, size and price remain
unknown. Licensed receipts: **zero**. No purchase/chargeable download was attempted.
See `phase3s_data_access.json`, `PHASE3P_DATA_ACCESS.md` and
`PHASE3S_FUTURES_PILOT.md`. The existing adapter/approval/reservation machinery was
not rebuilt. Futures research remains BLOCKED, not a successful zero-trade run.

Operator actions: configure provider access securely and approve exact quoted
requests; approve an unattended account/host; supply private independent backup
destination and key-custody policy; approve production TLS/ACLs and external security/
load review; arrange independent monitoring/paging and actual cutover/reboot/soak
tests. Continue genuine forward observations and independent futures research.
No frontend, paid infrastructure, broker connection, model retraining or trading
activation was performed.
