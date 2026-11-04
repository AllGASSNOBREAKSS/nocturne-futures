param(
    [Parameter(Mandatory = $true)][string]$Python,
    [string]$Repository
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
Set-Location $Repository
try {
    & $Python (Join-Path $Repository 'scripts/phase3h_shadow.py') --once --refresh
    $cycleExit = $LASTEXITCODE
    & $Python (Join-Path $Repository 'scripts/phase3i_forward_report.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    exit $cycleExit
} catch {
    Write-Error $_
    exit 1
}
