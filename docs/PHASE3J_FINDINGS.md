# Phase 3J — first-outcome readiness and unattended operations

Checkpoint: 2026-11-04 UTC. Branch `feat/phase3j`, base `0c56df7`.
This implements the received milestones 3J.1 and 3J.2; the received prompt ends
at the heading “Forward”. No additional milestone requirements were assumed.

## Verification and first forecast

Phase 3I reproduced **242 passing tests including native C++ parity**. Both
reported commits were independently verified green on GitHub Actions; latest run:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41776083342

Real refresh on November 4 at approximately 05:07 UTC returned NDX/VIX history
through **November 3 only**. The November 4 session has not opened. No outcome
exists and none was fabricated: **1 issued, 0 matured, 1 pending, 0 missed**.
Coverage, pinball and baseline comparisons remain unavailable, not zero.

The original timestamp is `2026-11-04T02:53:30.237804+00:00`, which was November 3
at 21:53 New York time. Original journal bytes still match `e963981`, SHA-256
`61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3`.
The frozen model, metadata and original predictions were not changed.

The first forecast remains legacy unadjusted inference, scored separately from
corrected inference. It has no pre-issued baseline embedded in its record;
baseline comparisons must not silently be presented as pre-issued evidence.

## Actual source revision detected

The refreshed November 3 NDX close is **28180.259765625**; the issued reference
is **28180.263671875**, a difference of -0.00390625 index points. Its small size
does not justify silently changing the original reference or relaxing the audit.
`REFERENCE_CLOSE_MISMATCH` remains a block on this forecast's evaluation.

The audit now includes both values, and local alerts expose the discrepancy.
The forecast is still PENDING because no outcome exists; operational status is
`AUDIT_BLOCKED`, not healthy. Before eventual evaluation, reconcile the revision
against independently verified archived issuance evidence through a reviewed
process. Do not edit the forecast, regenerate it, or substitute a revised
denominator. No reconciliation override was introduced in this checkpoint.

Quarantine is now per forecast. A failed historical record cannot suppress
unrelated forecasts' verified matured outcomes indefinitely. Existing complete-
bar, publication-bound, chronology, units and immutable-outcome rules remain.

## Durable local operational alerts

`shadow/operations.py` assesses:

- Missing, malformed, future-dated or older-than-90-minute cycle status.
- Explicit data blocks, audit blocks, failed cycles and provider refresh failures.
- Recent missed issuances (two-calendar-day alert window; full missed history stays).
- Outcomes absent after the source's next-UTC-midnight bound plus six hours.
- Calendar support boundaries and existing service health.

The 90-minute/six-hour windows are operational policies, not statistical model
thresholds or promises of provider publication time.

`alerts.jsonl` stores append-only OPEN/RESOLVED transitions under the existing
store lock with fsync. Repeated checks deduplicate; recurrence opens a new
transition. Missing or stale observations do not claim recovery of prior alerts.
Only fresh, explicitly successful audited cycles can resolve absent conditions.

`scripts/phase3j_operations.py` atomically writes
`reports/phase3j_operations.json` and returns nonzero on degradation. A real run
recorded **two open alerts**: unhealthy cycle and the first forecast audit block.
No external notification address, webhook or paging destination is configured.
Local journals and nonzero exit codes are not a claim that an operator was paged.

`GET /v1/shadow/operations` assesses current operations without writing incidents.
Data-health responses now surface audit/operational failure even if generation
was `EVALUATE_ONLY`. Forecasts remain read-only and `NO_TRADE` throughout.

## Scheduled execution and unattended support

The existing interactive task is preserved. Its runner now captures separate
per-stage stdout/stderr files under ignored `data/shadow/task-logs/`, executes
cycle/report/monitor stages even after an earlier stage fails, and propagates
failure to Task Scheduler. A real wrapper run returned exit 1 for the genuine
source-reference audit block. One-shot Python exceptions now write sanitized
failure status and structured logs instead of leaving stale successful status.
Generation failures no longer produce a successful-cycle heartbeat.

Installer additions:

- `-LogonMode Password` uses an explicitly supplied `PSCredential` and startup
  plus 30-minute triggers, independent of interactive login.
- Windows Task Scheduler protects the account credential. Scripts accept no
  plaintext password argument and never put passwords in task arguments, files,
  environment variables or diagnostics. Registration necessarily passes a
  temporary password string to the Windows API; this is not zero-exposure memory.
- `-WakeToRun` is explicit opt-in. It may wake a supported sleeping machine but
  cannot power on a shut-down host or guarantee firmware/battery policy behavior.
- Limited run level, no-overlap policy, bounded restart retries and execution
  time limits remain. Existing tasks are never overwritten automatically.

Both interactive and unattended task definitions passed **dry runs**. An actual
unattended task was **not registered or tested after logout**: no authorized
account credential was supplied. No privilege elevation or account changes were
performed. Current deployment still requires the logged-in user and awake host.

For an operator-authorized deployment, from a trusted local PowerShell session:

```powershell
$credential = Get-Credential
./scripts/install_shadow_task.ps1 -LogonMode Password -Credential $credential `
  -TaskName Nocturne-NDX-Unattended -WakeToRun
$credential = $null
```

Provision the dedicated account first: batch-logon rights, read/execute access to
the repository and isolated Python environment, write access to operational data,
logs/reports, outbound HTTPS, and only necessary data entitlements. Other-account
registration/startup triggers may require an elevated administrator installation;
the task itself should remain limited. Verify execution **under that account**,
then verify after logout and restart before disabling the old interactive task.
Never use SYSTEM or an administrator principal as a credentialless shortcut.

Use an always-on host or future authorized cloud VM for continuous availability.
An off-host monitor must check heartbeats and own paging; a sleeping/offline host
cannot run its own watchdog. Cloud provisioning, external alerts, account
credentials, log-retention policy and logout-independent availability remain
deployment requirements, not completed claims.

## Evidence and next steps

Local suite: **253 passed**, including native C++ parity. TypeScript typecheck
passed. Added tests cover deduplication/recovery/recurrence, stale/future status,
provider failures, missed deadlines, overdue horizons, read-only assessment,
exception sanitization/lock release and per-forecast evaluation eligibility.
Windows CI also dry-runs the unattended definition without registering a task.

Databento/FRED/BLS keys remain absent (presence checked without printing values).
Licensed NQ/ES history, trades/quotes/depth and authorized PIT calendars/news remain
blocked; no billable download, new empirical directional study or model promotion
was attempted. Only `ndx-range-v1` is shadow-active; all trading is `NO_TRADE`.

Next: review the archived-issuance/source-revision discrepancy, then await the
completed November 4 session and its verified availability bound (November 5
00:00 UTC in this adapter). Append an outcome only after both conditions pass.
Use an authorized account to complete the unattended rollout and configure an
off-host monitor before claiming continuous availability.
