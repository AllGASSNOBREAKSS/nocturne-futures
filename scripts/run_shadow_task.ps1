param(
    [Parameter(Mandatory = $true)][string]$Python,
    [string]$Repository
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
Set-Location $Repository
$logDirectory = Join-Path $Repository 'data/shadow/task-logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$run = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + "-$PID"
$exitCode = 0
$stageResults = @()
. (Join-Path $PSScriptRoot 'task_events.ps1')
$events = Join-Path $logDirectory "$run-events.jsonl"
Write-NocturneTaskEvent $events 'RUN_STARTED' @{ Lane = 'shadow' }
try {
    $guard = [IO.File]::Open((Join-Path $logDirectory 'task.wrapper.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
} catch [IO.IOException] {
    Write-NocturneTaskEvent $events 'RUN_FINISHED' @{ ExitCode = 75; Reason = 'BUSY_WRAPPER' }
    exit 75
}
try {
    $stages = @(
        @{ Name = 'cycle'; Script = 'scripts/phase3h_shadow.py'; Extra = @('--once', '--refresh') },
        @{ Name = 'audit'; Script = 'scripts/phase3l_forward_audit.py'; Extra = @() },
        @{ Name = 'report'; Script = 'scripts/phase3i_forward_report.py'; Extra = @() },
        @{ Name = 'monitor'; Script = 'scripts/phase3j_operations.py'; Extra = @() },
        @{ Name = 'health'; Script = 'scripts/phase3o_health.py'; Extra = @() }
    )
    foreach ($stage in $stages) {
        Write-NocturneTaskEvent $events 'STAGE_STARTED' @{ Stage = $stage.Name }
        try {
            # Direct invocation gives a reliable native exit code without detached
            # console/process-handle behavior. Stderr warnings are logged, not
            # mistaken for terminating PowerShell errors when exit code is zero.
            $stagePath = Join-Path $Repository $stage.Script
            $extra = $stage.Extra
            $LASTEXITCODE = $null
            try {
                $ErrorActionPreference = 'Continue'
                & $Python $stagePath @extra 1> (Join-Path $logDirectory "$run-$($stage.Name).out.log") 2> (Join-Path $logDirectory "$run-$($stage.Name).err.log")
                $stageExit = $LASTEXITCODE
            } finally { $ErrorActionPreference = 'Stop' }
            if ($null -eq $stageExit) { throw 'Python process returned no exit code' }
            $stageResults += @{ Stage = $stage.Name; ExitCode = $stageExit }
            Write-NocturneTaskEvent $events 'STAGE_FINISHED' @{ Stage = $stage.Name; ExitCode = $stageExit }
            if ($stageExit -ne 0) { $exitCode = 1 }
        } catch {
            # Continue to the independent monitor even if an earlier stage failed.
            Add-Content -Path (Join-Path $logDirectory "$run-runner.err.log") -Value $_.Exception.GetType().Name
            $stageResults += @{ Stage = $stage.Name; ErrorType = $_.Exception.GetType().Name }
            Write-NocturneTaskEvent $events 'STAGE_ERROR' @{ Stage = $stage.Name; ErrorType = $_.Exception.GetType().Name }
            $exitCode = 1
        }
    }
} catch {
    Add-Content -Path (Join-Path $logDirectory "$run-runner.err.log") -Value $_.Exception.GetType().Name
    $exitCode = 1
}
$stageResults | ConvertTo-Json | Set-Content -Encoding UTF8 -Path (Join-Path $logDirectory "$run-stages.json")
Write-NocturneTaskEvent $events 'RUN_FINISHED' @{ ExitCode = $exitCode }
$guard.Dispose()
exit $exitCode
