[CmdletBinding()]
param(
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [string]$Repository,
    [int]$BudgetSeconds = 900,
    [int]$MaxJobs = 20
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
Set-Location $Repository
$logs = Join-Path $Repository 'data/research/orchestrator/task-logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$run = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + "-$PID"
$LASTEXITCODE = $null
try {
    $ErrorActionPreference = 'Continue'
    & $Python (Join-Path $Repository 'scripts/phase3m_research.py') --lane research --budget-seconds $BudgetSeconds --max-jobs $MaxJobs 1> (Join-Path $logs "$run.out.log") 2> (Join-Path $logs "$run.err.log")
    $code = $LASTEXITCODE
} finally { $ErrorActionPreference = 'Stop' }
if ($null -eq $code) { exit 1 }
exit $code
