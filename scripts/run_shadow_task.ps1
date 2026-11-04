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
try {
    $stages = @(
        @{ Name = 'cycle'; Script = 'scripts/phase3h_shadow.py'; Extra = '--once --refresh' },
        @{ Name = 'report'; Script = 'scripts/phase3i_forward_report.py'; Extra = '' },
        @{ Name = 'monitor'; Script = 'scripts/phase3j_operations.py'; Extra = '' }
    )
    foreach ($stage in $stages) {
        try {
            $arguments = '"{0}" {1}' -f (Join-Path $Repository $stage.Script), $stage.Extra
            $process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $Repository `
                -RedirectStandardOutput (Join-Path $logDirectory "$run-$($stage.Name).out.log") `
                -RedirectStandardError (Join-Path $logDirectory "$run-$($stage.Name).err.log") -Wait -PassThru
            if ($process.ExitCode -ne 0) { $exitCode = 1 }
        } catch {
            # Continue to the independent monitor even if an earlier stage failed.
            Add-Content -Path (Join-Path $logDirectory "$run-runner.err.log") -Value $_.Exception.GetType().Name
            $exitCode = 1
        }
    }
} catch {
    Add-Content -Path (Join-Path $logDirectory "$run-runner.err.log") -Value $_.Exception.GetType().Name
    $exitCode = 1
}
exit $exitCode
