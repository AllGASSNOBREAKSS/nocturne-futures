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
. (Join-Path $PSScriptRoot 'task_events.ps1')
$events = Join-Path $logs "$run-events.jsonl"
Write-NocturneTaskEvent $events 'RUN_STARTED' @{ Lane = 'research' }
try {
    $guard = Open-NocturneTaskGuard (Join-Path $logs 'task.wrapper.lock') $events
} catch [IO.IOException] {
    Write-NocturneTaskEvent $events 'RUN_FINISHED' @{ ExitCode = 75; Reason = 'BUSY_WRAPPER' }
    exit 75
}
try {
    $ErrorActionPreference = 'Continue'
    & $Python (Join-Path $Repository 'scripts/phase3m_research.py') --lane research --budget-seconds $BudgetSeconds --max-jobs $MaxJobs 1> (Join-Path $logs "$run.out.log") 2> (Join-Path $logs "$run.err.log")
    $code = $LASTEXITCODE
} catch {
    Write-NocturneTaskEvent $events 'RUN_ERROR' @{ ErrorType = $_.Exception.GetType().Name }
    $code = 1
} finally { $ErrorActionPreference = 'Stop' }
if ($null -eq $code) { $code = 1 }
Write-NocturneTaskEvent $events 'RUN_FINISHED' @{ ExitCode = $code }
$guard.Dispose()
exit $code
