# Phase 3T — forecast quarantine and scoped operational recovery

November 8, 2026 UTC; branch `feat/phase3t`, base `d69f853`.
**NO_GO_FRONTEND / NO_PROMOTION / NO_TRADE.** No arbitrary 70% assessment.

## Baseline verification

The starting tree was clean. Actual Phase 3S HEAD was `d69f853`, independently
confirmed five-job CI-successful in run **42464563825**, not merely assumed from
`c5de881`. Evidence: `reports/phase3t_baseline_ci.json`. Existing security,
hash-locked numerical versions, registry, pythonw scheduling and orchestration were
retained. No frozen model, prediction, denominator, source object or outcome was
rewritten. No new trading model was fitted or promoted.

## 3T.1 — both incidents classified; neither independently cleared

The existing issuance/reconciliation verifier reproduces archived features and
dataset digests exactly, checks the sealed forecast, compares raw quote versus
adjusted close and upstream instrument/timezone/session timestamps, and binds the
entire revised reference bar. A new read-only disposition composes these checks;
it does not append an executable reconciliation proof or authorize an outcome.

- **November 6 — `291aac9c9d893a888609aafd`.** Original reference
  **26629.80859375**, revised **26629.810546875**, difference **+0.001953125**
  points. Reference date November 5. Issued November 6 00:47:12.720972 UTC;
  original receipt 00:47:09.891512 UTC. The target bar is now present, provider-OHLC
  complete and beyond the November 7 00:00 UTC bound, but independently verified
  final outcome high/low are absent. **AUDIT_BLOCKED**, not eligible for evaluation.
- **November 9 — `cd26071237a957cd7a874933`.** Original reference
  **26989.9921875**, revised **26989.990234375**, difference **−0.001953125**
  points. Reference date November 6. Original issue November 7 00:17:13.154782 UTC.
  November 9 has not occurred; the November 10 00:00 UTC availability bound has not
  elapsed and no complete target bar exists. Reference integrity also remains
  blocked. **AUDIT_BLOCKED / time-pending**, not eligible for evaluation.

For both, upstream payload values demonstrably changed, including volume. Inspected
reference rows retain matching exchange timestamps/instrument/timezone; quote close
equals adjusted close. There is no evidence here of a session-alignment defect or
adjusted-close substitution. The provider's internal revision reason and exchange
finality are **unconfirmed**, so the disposition is
`OBSERVED_PROVIDER_REVISION_FINALITY_UNVERIFIED`, not a declaration of legitimate
exchange-final prices. Numerical software error is not supported by exact issuance
input/four-forecast inference replay; that does not establish market truth.

One bounded public-reference check per eligible session/provider was made. FRED
failed by connection/timeout; Nasdaq returned 404/unavailable. Even a FRED close
would not authenticate final target high/low. No repeated Databento downloads,
paid request, access-control workaround or synthetic replacement was attempted.

Per-forecast reports include original/revised values and differences, issuance/
source/exchange timestamps, source identities/hashes, raw changes, independent
attempts, target completeness/availability, verdict and blocking reasons:
`phase3t_incident_2026-11-06.json`, `phase3t_incident_2026-11-09.json`.
Disposition objects are preserved content-addressed under private snapshot archive
`incident-dispositions/`; public summary: `phase3t_incidents.json`. Original forecast,
outcome and reconciliation bytes were unchanged by investigation. No proof was
applied. Independent final OHLC evidence and deliberate review are still required;
never change denominators or loosen tolerances to clear these incidents.

## 3T.2 — distinguish completion, issuance and integrity

Added separate operational components for **service execution**, **forecast issuance**
and **evaluation quarantine**. Fresh audit-blocked completion is not a process crash
or host-uptime guarantee. Aggregate health remains degraded, all unresolved alerts
remain open and existing Windows shadow task exit **1** remains nonzero. A recent
completed quarantine is distinguished from a stale heartbeat or exception. Old
fully healthy-cycle timestamps are retained separately from recent completed work.

Fixed a real classification defect: historical audit failure previously took
precedence over concurrent issuance failure. Failed generation now retains
`CYCLE_FAILED` even when older forecasts are quarantined; neither condition hides
the other. Unknown/stale/malformed reports never imply healthy execution/integrity.

The research DAG previously mapped every nonzero shadow subprocess exit to software
failure, suppressing downstream work. It now consumes a **new exclusive per-attempt
receipt**, never a possibly stale shared status file. A scoped refresh/issuance/
maturity operation can complete while older outcomes remain quarantined only when
the receipt proves that exact operation completed and binds the quarantined IDs.
The original exit **1**, receipt hash, quarantine IDs and `AUDIT_BLOCKED` remain in
its result. Job state SUCCEEDED means **scoped operation completion only**; job
health still classifies such results **BLOCKED**, not healthy data. Refresh failure,
failed generation, missing/malformed receipt, exception and wrong exit cannot take
this path. Lock contention now returns **75**, never false successful work.

Added local alert acknowledgement to the existing append-only journal. It records
bounded actor/reason identifiers and retains state OPEN; it cannot resolve/silence
an alert, waive a gate or enable trading. No live incident was acknowledged merely
to improve health. Example for an authorized operator (no credentials/free text):

```powershell
python scripts/phase3j_operations.py --ack-alert FORECAST_AUDIT:291aac9c9d893a888609aafd --actor operator --reason-code INVESTIGATING
```

The monitor still returns nonzero while unresolved issues exist. Existing evidence-
based resolution remains; acknowledgement history is never erased.

Synthetic lifecycle regression tests cover future issuance while older records are
quarantined, idempotent retries, independent allowed-ID maturity evaluation, restart
store access, lock release/contention, failure precedence, stale reports, corrupted
issuance, non-authoritative independent-check flags and ack/resolution. These are
engineering fixtures, not forward observations or market-performance evidence.

## 3T.3–3T.5 — real work performed and external research limit

The existing shadow lane executed **five genuine job types**: refresh, forecast
request, maturity check, forward audit and drift/report generation. The existing
November 9 issue was returned idempotently; no duplicate forecast or forced outcome
was created. A concurrent bounded research tick executed **zero new research jobs**:
daily validation was already eligible/completed and missing futures inputs retain
cached BLOCKED identities. Two research-report jobs updated. No exhausted index
experiment, new ML fit or exposed holdout selection was repeated.

`phase3t_assurance.json` inventories all 12 types and actual phase-window updates,
including exit/quarantine evidence. Reporting/drift checks ran, but two outcomes
remain insufficient for a statistical drift estimate or predictive-accuracy claim.

Two genuine exercised completions per deployed task have complete launcher/stage
receipts: shadow **1** (quarantine), research **0**, with no crash/hang claim. Four
operational alerts remain open: cycle unhealthy, two forecast audits and November 6
overdue evaluation. State: **4 issued / 2 verified matured / 2 pending / 0 missed**;
one verified outcome in each inference cohort. `phase3t_scheduler.json`.
Actual live tasks remain Interactive/awake/logged-in. No task principal/trigger/
action/settings change, public listener, paid infrastructure or reboot/logoff test.

Databento/FRED/BLS/Nasdaq Data Link credentials are absent in checked process/user/
machine scopes. Licensed futures receipts **zero**; GLBX.MDP3 entitlement, credits,
resolved IDs, actual quote/price and consumption approval remain **unverified**.
`phase3t_external_access.json`: **USER_ACTION_REQUIRED**, no paid consumption.
The exact operator path remains `PHASE3S_FUTURES_PILOT.md` and
`PHASE3P_DATA_ACCESS.md`; no acquisition system was rebuilt.

The first authentic futures cycle is **externally BLOCKED**, not a zero-trade success.
No bullish/bearish, consolidation, profile reaction, aggressor-flow, target-first or
time-to-target finding was produced. 100/200/350/500-point NQ probabilities remain
unsupported/null. Validated licensed contract history, costs, chronological purged/
embargoed folds, separate calibration and untouched observations are prerequisites.
Cash indices and old continuous proxies do not meet them.

## 3T.6 — tests, security and recovery

Core implementation **`fcac56c`** passes **429 tests** locally and in the existing
isolated locked environment, including native parity, API auth/roles/limits/audits,
real TLS and encryption/tamper rejection. All **five CI jobs green** in run
**42465576451** at that exact commit. `phase3t_tests.json`, `phase3t_ci.json`.
The isolated venv/native build was reused, not recreated. Installed-file audit
verifies **13,458 hashes** and all **four original issued forecast cases** exactly;
`phase3t_runtime.json`. No numerical dependency, model artifact or security boundary
changed.

Follow-up fix **`6bd0f75`** stops the audit from falling back to a close-only
comparison once a full-bar reconciliation is bound to a forecast; a regression test
covers it. At `6bd0f75`, **431 tests** pass locally and in a **new** isolated locked
environment (`nocturne-phase3t-final`, fresh native build, 13,458 hashes and four
exact inference replays). The earlier `nocturne-phase3s-final` venv's `python.exe`
was absent again on November 9 (cause unknown; directory preserved). TypeScript
passes. All **five CI jobs green** in run **42466314331** at `6bd0f75`.
Report-only evidence commits after it have separate CI scope.

Existing encrypted private backup is tested through the existing restore CLI into
a new permitted isolated local directory, without activating its services. The
backup contains the November 6 recovery point (three forecasts/two outcomes), not
current four-issue state. Independent destination/key-custody approval remains
absent: **OFF_HOST_VERIFICATION_REQUIRED**. Same-host temporary demo custody and
local timings do not achieve proposed RPO 30m/RTO 60m. API external ACL/TLS lifecycle/
load review, unattended hosting, hard memory isolation and independent paging are
still open. No public or paid deployment was activated.

The current restore authenticated and replayed **765 files in 20.64s**, verified
the original three-issue/two-outcome recovery point and six cached challenger
hashes, and reproduced the two previously negative index diagnostics solely as
recovery checks. It made zero network requests and trained zero models. These are
not new research findings or independent NQ/ES strategy validation.

## Acceptance

Evidence-backed incident dispositions and operational isolation are implemented;
independent clearance of the two outcomes is **not** established. See
`BACKEND_READINESS.md`, `phase3t_acceptance.json` and `IMPLEMENTATION_CHECKPOINT.md`.
Engineering acceptance remains partial at external deployment/recovery gates;
quantitative acceptance remains blocked by authentic independent futures evidence.
No completion percentage, model promotion, frontend or trading approval follows.
