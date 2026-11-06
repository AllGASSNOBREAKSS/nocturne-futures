# Phase 3Q — staged deployment and private recovery runbook

## Supported and tested scope

Windows x64, CPython 3.14.6, PowerShell, Git, MSVC C++20 tools/Windows SDK;
dependencies pinned in `requirements/windows-py314.lock.txt`. A new isolated venv,
independent local Git clone, fresh native build and private-evidence restore were
tested on the existing host. This is **not a separate OS/host deployment test**.
Python 3.12 Linux/Windows CI is a separate compatibility check, not this lock's scope.

Public Git does not restore private source archives, licensed data, consumption
reservations, historical experiment files or SQLite state. Never upload a recovery
archive to a public repo/artifact or transfer licensed data without permission.
No authorized off-host destination has been supplied. Off-host backup, encryption,
retention and separate-machine recovery remain operator actions, not achieved gates.

## 1. Prepare a new, non-active deployment

Use an operator-approved private directory and least-privilege account. Install
CPython 3.14 x64, PowerShell, Git and the MSVC C++ toolchain/Windows SDK through
approved mechanisms. Do not copy a venv or compiled `.pyd` between machines.
For resuming historical research jobs, preserve the recorded project root/path:
old SQLite results contain immutable absolute artifact paths. A different root is
supported for **offline mapped verification only**, not automatic job resumption.

Check out the reviewed deployment commit, then in PowerShell:

```powershell
python -m venv .venv
$py = (Resolve-Path .venv/Scripts/python.exe).Path
& $py -m pip install -r requirements/windows-py314.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $py -m pip install --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
& $py -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
```

The lock is Windows/3.14-specific and version-pinned, not wheel-hash locked. Package
index/wheel availability and supply-chain review remain deployment prerequisites.
Do not run a blanket dependency upgrade: an initial clean resolution with
NumPy 2.5.4/pandas 3.1.1 passed 361 tests but failed exact real issuance replay.
NumPy 2.5.0/pandas 3.0.3 restore the exact proof. Never rewrite evidence or loosen
audit comparisons to accommodate dependency changes.

## 2. Build and test native code

Open an x64 Visual Studio Developer PowerShell/command environment. The Phase 3Q
drill used MSVC 19.51, CMake 4.4.4, Ninja 1.13.2 and pybind11 3.1.0. In PowerShell:

```powershell
$py = (Resolve-Path .venv/Scripts/python.exe).Path
$env:PATH = "$(Resolve-Path .venv/Scripts);$env:PATH"
$bind = & $py -m pybind11 --cmakedir
cmake -S native -B native/build -G Ninja -DCMAKE_BUILD_TYPE=Release "-Dpybind11_DIR=$bind" "-DPYTHON_EXECUTABLE=$py"
if ($LASTEXITCODE -ne 0) { throw 'Native configure failed' }
cmake --build native/build
if ($LASTEXITCODE -ne 0) { throw 'Native build failed' }
$env:PYTHONPATH = (Resolve-Path native/build).Path
$env:PYTHONNOUSERSITE = '1'
& $py -m pytest -o addopts='' -q --junitxml=isolated-tests.xml
if ($LASTEXITCODE -ne 0) { throw 'Regression/parity tests failed' }
```

Confirm the native module comes from this build, not the source machine or a
global installation. `scripts/phase3q_environment.py` checks package/native paths,
venv isolation, all pins and JUnit counts. See `reports/phase3q_environment.json`.
CMake currently emits legacy Python-finder policy warnings; the build succeeds.

## 3. Restore evidence before activating anything

1. On the source host, keep manual acquisition/reconciliation writers quiescent.
   Use the existing bounded snapshot command at a non-deadline time:
   `python scripts/phase3p_recovery.py --report-prefix phase3q_recovery snapshot --destination <new-private-snapshot>`.
   Busy cooperating writers cause a failure, never forced termination.
2. Transfer only to an authorized private destination, retaining the manifest and
   its checksum plus a separately protected expected checksum. This step was **not
   performed off-host**. Protect access/retention/encryption outside this tool.
3. With matching reviewed code and the pinned venv, run:
   `python scripts/phase3p_recovery.py --report-prefix phase3q_recovery check --snapshot <private-snapshot> --restore-to <new-private-evidence-root>`.
4. Require all exact file/SQLite/issuance/outcome checks and fixed-diagnostic replay
   to pass. A failed or mismatched restore is quarantined, not repaired in place.
5. Keep the restored evidence root unchanged as the recovery proof. No restored
   scheduler or service is activated by the verifier. Mutable market caches are
   deliberately absent; the existing guarded refresh must reconstruct them before
   any live operation. Do not invent cache manifests from archived bar values.

The real drill captured 654 files / 228,647,450 bytes. Manifest SHA-256:
`b3eaf5a1526f1c6e9ce61f68c179654e1f13dc26c2ea17b1db70ede613e63bf3`.
After pinning the numerical runtime, all three forecast proofs, two outcomes and
six saved challenger hashes verify, and the two original fixed index diagnostics
reproduce exactly. Reports: `phase3q_recovery_*.json`.

## 4. Initialize state without erasing historical state

`JobStore(<new-runtime-state>)` initializes a fresh SQLite database through the
existing implementation; do not manufacture a schema or copy a live SQLite file.
The drill initialized zero jobs in new state and executed one actual nine-source
DATA_VALIDATION job against restored history, then reverified captured bytes.
See `reports/phase3q_clean_validation.json`.

A fresh runtime is not a replacement for historical job/event records. Preserve
the recovered database as evidence. Resuming it at the same recorded project root
requires reviewing all referenced artifact paths/receipts. At a different root,
use offline verification; a reviewed runtime-path migration/cutover is still
required. Do not rewrite the immutable archived SQLite database or blindly replay
old training jobs. Default research does not opt into old index diagnostics.

## 5. Secrets and live cutover — explicit operator gate

- Configure secrets locally through the approved secret mechanism. Do not put
  values in task arguments, logs, Git, `.cmd` files or chat. Task credentials must
  be supplied as `PSCredential`, never a command-line password.
- Futures acquisition is `USER_ACTION_REQUIRED`; follow the single exact checklist
  in `PHASE3P_DATA_ACCESS.md`. No new provider access or spending is authorized here.
- Keep the existing issuer as the sole active issuer until cutover is approved.
  Before any transition, stop accepting new work, wait for active jobs or their
  bounded watchdogs, snapshot consistently, verify all journal prefixes/model
  hashes and account for any newly issued/matured observations. Never delete locks
  or consumption reservations to force progress.
- Installing restored evidence into a deployment root is an operator-controlled
  step after verification, with no producer running. Preserve exact bytes and do
  not overwrite conflicting files. No automated live-state overlay was added.
- Run read-only audits/reports first, then the existing guarded refresh/evaluation
  on the sole intended runtime. Any source revision/audit failure blocks it; no
  automatic reconciliation or backdated prediction is allowed.

## 6. Register tasks and prove scheduled completion

Dry-run only, in the staged deployment:

```powershell
./scripts/install_shadow_task.ps1 -Python $py -WhatIf
./scripts/install_research_task.ps1 -Python $py -WhatIf
```

Installers refuse to overwrite existing tasks. They now use the interpreter's
matching `pythonw.exe` and the standard-library `run_headless_task.py`, which invokes
the existing PowerShell runner with `CREATE_NO_WINDOW`. No console is allocated;
native exit codes, timeout failures (124), stage errors and wrapper busy (75)
remain failures. Startup/finish events are append-only and fsynced. A killed run
has no synthetic success receipt. Existing orchestrator recovery, budgets,
dependencies, OS locks, retries and child watchdogs remain in use.

Current host tasks retain Interactive/Limited principals, 30-minute/six-hour
triggers, restart counts and 20-/18-minute task limits. Only actions changed; XML
comparison verifies unchanged principals/settings/triggers. Parent launcher
deadlines (19/17 minutes) precede scheduler limits. External forced termination
can still leave unmatched lifecycle starts; later runs must inspect/recover, not
erase those records. Hard memory isolation and long-duration soak remain untested.

After authorized registration/cutover:

```powershell
./scripts/phase3q_scheduler.ps1 -Exercise -Repetitions 3
```

Require real Task Scheduler exit 0 and matching complete launcher/runner receipts
for every run, not just direct CLI success. Use the script without `-Exercise` for
a read-only last-run check. It does not suppress nonzero statuses.

Interactive mode **requires the host awake and user logged in**. For logout-
independent shadow operation, the existing installer supports `-LogonMode Password
-Credential (Get-Credential)`; the operator must approve and provide an appropriate
account. Research service-account registration also requires operator review.
Neither authenticated service-account mode nor reboot/logoff/power-off operation
was exercised. No account/password/security policy or logging policy was changed.
No always-on infrastructure or independent paging has been deployed.

## 7. Health, rollback and unresolved acceptance

Run `phase3l_forward_audit.py`, `phase3i_forward_report.py`,
`phase3j_operations.py`, `phase3o_health.py`, then the scheduler last-run inspection.
Green core reports cannot override a failed task exit or incomplete lifecycle.
The read-only API remains local/non-production; external authentication, TLS,
authorization, rate limits/load and network exposure require a separate review.

Task definitions from before changes are private in
`data/recovery/phase3q-task-definitions/`. An operator can restore only their saved
Actions with `Set-ScheduledTask -Action`; preserve principals/settings/triggers.
The old console action had intermittent interruptions: rollback restores prior
behavior, not a guarantee of reliability. Do not delete/re-register tasks to hide
history. Roll code/environment back only to a proof-compatible version, keeping
all new forecasts/outcomes/receipts and reservations; never Git-reset live journals.
Re-audit before resuming. A separate-host cutover/rollback drill remains untested.

**NO-GO frontend:** isolated-environment success does not close separate-host,
off-host durability, unattended account, API deployment/security, independent
monitoring or authentic quantitative-data/calibration gates.
