[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Environment,
    [Parameter(Mandatory = $true)][string]$Wheelhouse,
    [string]$Repository,
    [switch]$BuildNative,
    [ValidateSet('numerical','security')][string]$Profile = 'numerical'
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
$Repository = (Resolve-Path $Repository).Path
$Wheelhouse = (Resolve-Path $Wheelhouse).Path
$Python = (Resolve-Path $Python).Path
if (Test-Path $Environment) { throw 'Environment destination must be new; no in-place upgrades.' }
if ($BuildNative -and (Test-Path (Join-Path $Repository 'native/build'))) { throw 'Native build directory must be absent; use a new source checkout.' }
& $Python -I -c "import sys,platform; assert sys.platform=='win32' and sys.version_info[:2]==(3,14) and platform.machine().lower()=='amd64', 'Lock target is Windows x64 CPython 3.14'"
if ($LASTEXITCODE -ne 0) { throw 'Wrong interpreter target' }
if ($BuildNative -and -not (Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    throw 'Use an x64 MSVC Developer shell; compiler/SDK installation is an operator prerequisite.'
}
$priorPythonPath = $env:PYTHONPATH
try {
    # The lock verifier imports only stdlib code before dependencies exist.
    $env:PYTHONPATH = Join-Path $Repository 'src'
    & $Python (Join-Path $Repository 'scripts/phase3r_lock.py') --wheelhouse $Wheelhouse --profile $Profile
    if ($LASTEXITCODE -ne 0) { throw 'Wheel integrity verification failed' }
    & $Python -m venv $Environment
    if ($LASTEXITCODE -ne 0) { throw 'Venv creation failed' }
    $py = Join-Path (Resolve-Path $Environment).Path 'Scripts/python.exe'
    $lockName = 'windows-py314.hashes.txt'
    if ($Profile -eq 'security') { $lockName = 'windows-py314-security.hashes.txt' }
    & $py -m pip install --no-index --only-binary=:all: --find-links $Wheelhouse --require-hashes -r (Join-Path $Repository "requirements/$lockName")
    if ($LASTEXITCODE -ne 0) { throw 'Hash-locked offline install failed' }
    & $py -m pip install --no-index --no-deps --no-build-isolation -e $Repository
    if ($LASTEXITCODE -ne 0) { throw 'Offline editable package build failed' }
    & $py -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed' }
    $env:PYTHONPATH = ''
    if ($BuildNative) {
        $cmake = Join-Path (Split-Path $py -Parent) 'cmake.exe'
        $ninja = Join-Path (Split-Path $py -Parent) 'ninja.exe'
        $bind = & $py -I -m pybind11 --cmakedir
        & $cmake -S (Join-Path $Repository 'native') -B (Join-Path $Repository 'native/build') -G Ninja -DCMAKE_BUILD_TYPE=Release "-DCMAKE_MAKE_PROGRAM=$ninja" "-Dpybind11_DIR=$bind" "-DPYTHON_EXECUTABLE=$py"
        if ($LASTEXITCODE -ne 0) { throw 'Native configure failed' }
        & $cmake --build (Join-Path $Repository 'native/build')
        if ($LASTEXITCODE -ne 0) { throw 'Native build failed' }
    }
    $extra = @()
    if ($BuildNative) { $extra += '--native' }
    if ($Profile -eq 'security') { $extra += '--security' }
    & $py (Join-Path $Repository 'scripts/phase3r_verify.py') --repository $Repository --output (Join-Path $Repository 'reports/phase3r_runtime.json') @extra
    if ($LASTEXITCODE -ne 0) { throw 'Installed integrity/inference verification failed' }
} finally { $env:PYTHONPATH = $priorPythonPath }
# Deliberately no task registration, secret injection, network data fetch or service activation.
