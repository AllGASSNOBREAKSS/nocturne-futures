# Phase 3R — locked bootstrap, numerical replay and recovery objectives

## Trust and supported target

The full wheel lock targets **Windows x64 / CPython 3.14**. The local drill uses
CPython 3.14.6, MSVC 19.51, CMake 4.4.4, Ninja 1.13.2 and pybind11 3.1.0.
Separate Python 3.12 CI uses the six numerical constraints, not the Windows wheel
lock. No cross-platform or cross-compiler bitwise-binary claim is made.

`requirements/windows-py314.hashes.txt` binds **55 runtime/dev/build wheels**.
`windows-py314.wheels.json` records exact filenames, sizes and SHA-256 checked
against their exact current PyPI release entries over HTTPS. Total wheel bytes:
**141,178,373**. Binaries remain ignored in `data/recovery/phase3r-wheelhouse/`.
The original 3Q runtime lock remains unchanged; build tools have a separate lock.

These hashes protect reviewed package bytes, not publisher identity or malware
absence. Installed RECORD checks detect accidental file drift against trusted
local metadata; RECORD/bytecode without declared hashes is excluded. An operator
able to rewrite both metadata and payload can defeat that check. Base Python,
bundled pip, OS/MSVC/SDK provenance and secure distribution of trusted lock files
remain deployment trust prerequisites. No secret values or licensed data are in
the wheel metadata or public reports.

## Offline bootstrap

Start with a new reviewed checkout and absent venv/native-build destinations. In
an x64 MSVC Developer PowerShell, with a local reviewed wheelhouse:

```powershell
./scripts/bootstrap_locked_environment.ps1 -Python C:/Python314/python.exe -Environment <new-private-venv> -Wheelhouse <reviewed-wheelhouse> -Repository <reviewed-checkout> -BuildNative
```

The script checks the target and wheel bytes, creates a new venv, runs pip with
`--no-index --require-hashes --only-binary=:all:`, builds the local package with
`--no-deps --no-build-isolation`, checks dependencies, compiles existing native
sources, and verifies installed hashes/model inference. It never installs tasks,
injects secrets, fetches market data or activates a restored issuer. Compiler/SDK
installation is an operator prerequisite, not an automatic system modification.
Failures leave evidence/directories for review; no in-place upgrade or broad
cleanup is performed.

For an authorized initial public-package staging download, pip can enforce the
already-reviewed hashes directly:

```powershell
python -m pip download --only-binary=:all: --no-deps --require-hashes --dest <new-wheelhouse> -r requirements/windows-py314.hashes.txt
python scripts/phase3r_lock.py --wheelhouse <reviewed-wheelhouse>
```

The lock-generation `--create` mode was used once against actual downloaded wheels
and upstream metadata. It refuses to overwrite existing locks. Do not regenerate
locks to make a failing deployment appear approved.

## Frozen inference and upgrade approval

The frozen model loader now rejects unapproved NumPy, pandas, SciPy, scikit-learn,
LightGBM and joblib versions **before pickle loading/inference**. Current approved
versions are in `frozen-shadow.constraints.txt` and `FROZEN_NUMERICAL_RUNTIME`.
The full offline runtime also records every locked package version and verifies
13,290 hashed installed files. Reports include Python/platform, source commit,
tracked-code cleanliness, native binary digest and CMake compiler/build settings.

All three immutable issued rows serve as golden inference cases: the original
legacy-unadjusted cohort is compared without residual adjustments, later rows with
the frozen residual-adjusted-v1 method. Outputs must match exact float hexadecimal
values, not a widened tolerance. Tests reject a one-ULP changed expected quantile,
unknown cohorts, wrong identity, duplicate rows and version drift before model load.
No frozen model, forecast, outcome or original denominator is rewritten.

Stored-feature replay is **not** full upstream reconstruction. For the latter,
also run the existing original archived issuance/outcome proof checks and fixed
historical diagnostic replay. The 3Q rejected NumPy/pandas upgrade remains rejected;
there was no reason to repeat that known failure or tune against exposed holdouts.

For a genuinely proposed upgrade:
1. Create a separate review branch and new environment/lock candidate; never modify
   the active venv or frozen artifact in place. An unapproved runtime must remain
   blocked in the production loader.
2. Record exact wheels, versions, source/build hashes and expected platform.
3. Run all regressions/native parity, the unchanged golden inference rows, and full
   private archived-source/SQLite/outcome replay with matching reviewed code.
4. Treat any numerical, parser, feature, denominator or source-proof difference as
   a blocked candidate. Do not regenerate historical expected outputs or increase
   comparison tolerances. A real method change needs a new challenger/version and
   independently eligible evidence, never an in-place promotion.
5. Only a separately reviewed successful candidate can change approved runtime
   pins. Keep rollback environment/artifacts and the original expected evidence.

## Private recovery and scheduling priority

Use the existing snapshot/restore CLI with a new prefix/destination:

```powershell
python scripts/phase3p_recovery.py --report-prefix phase3r_recovery snapshot --destination <new-private-snapshot>
python scripts/phase3p_recovery.py --report-prefix phase3r_recovery check --snapshot <trusted-private-snapshot> --restore-to <new-private-location>
```

Keep non-cooperating manual writers quiescent. Capture checks real Windows task
deadlines before locking, defers if a tick is within its budget plus 15 seconds,
and limits live scheduled-host capture to 30 seconds. Existing cash-open exclusion
and non-blocking producer locks remain. If a manual/restart launch races capture,
the wrapper distinguishes a shared backup byte lock from another deny-share
wrapper. Backup contention waits at most 45 seconds, then remains a nonzero busy
failure; a true overlapping wrapper still fails immediately with 75. No result is
silently remapped to success. Source/journal/SQLite consistency is not weakened.

This addresses a **real** 01:47 UTC collision: the 10.69-second capture held the
guard when the scheduled tick arrived, which correctly returned 75. Failure
evidence remains in `reports/phase3r_backup_collision.json`. Never delete it to
claim uninterrupted operation. Tests reproduce the admission boundary and real
Windows byte-lock wait/release; completed scheduled runs are checked separately.

The verified drill captured **688 files / 231,067,330 bytes**, manifest SHA-256
`eb8f02654c05855106d44efe3c660c3d27201f768c36a9b80de578016ce54bea`.
Offline restoration and full proof/diagnostic replay took **13.70 seconds** locally;
it verified 3 forecast proofs, 2 outcomes, six saved challenger hashes and the two
old fixed index diagnostics. That elapsed time excludes provisioning, transfer,
credential setup, task activation and live cutover. No restored issuer was started.

The broader installation, task/secrets/cutover/rollback procedure remains
`PHASE3Q_DEPLOYMENT.md`; its manual dependency-install section is superseded by
this offline bootstrap for the Windows 3.14 target. Historical SQLite absolute
artifact paths still prevent blind live resumption at an arbitrary relocated root.
Mapped offline verification is not a runtime-path migration.

## RPO/RTO proposals — not achieved off-host SLOs

- Proposed **RPO: 30 minutes** for coherent journals, source objects, model pins,
  reservations and research SQLite state. There is no automated approved off-host
  backup cadence; a total-host-loss RPO is therefore unbounded/unverified.
- Proposed **RTO: 60 minutes** after approved host/toolchain/private backups and
  credentials are available. The 13.70-second local replay is not this end-to-end
  recovery objective. Separate-host provisioning/cutover has not been tested.
- The hosted Windows CI job independently verifies public-code bootstrap and the
  already-public frozen model/issued feature cases. It receives no private source
  archive, SQLite recovery image, credentials or licensed data, so its success is
  not a private off-host restore or operational cutover demonstration.
- Operator must approve the objectives, an authorized private off-host destination,
  encryption/access/retention policy and separate key custody, then demonstrate
  recovery on an independent host. No encrypted off-host copy, password, account or
  paid infrastructure was created here. Existing local drill copies are plaintext
  unless separately protected by host controls; encryption was not verified.

Frontend and trading remain blocked by the broader deployment and quantitative
gates. Neither successful package integrity nor recovery timing establishes an
independent futures forecasting edge.
