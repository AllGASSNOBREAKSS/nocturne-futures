[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [string]$Repository,
    [string]$TaskName = 'Nocturne-NDX-ReadOnly-Shadow'
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
$Python = (Resolve-Path $Python).Path
$Repository = (Resolve-Path $Repository).Path
$runner = Join-Path $Repository 'scripts/run_shadow_task.ps1'
# No credentials stored; this deployment runs only while this user is logged in.
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $Repository -Argument (
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Python "{1}" -Repository "{2}"' -f $runner, $Python, $Repository
)
$triggers = @(
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)),
    (New-ScheduledTaskTrigger -AtLogOn -User $user)
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Task already exists; inspect it before changing or removing it: $TaskName"
}
if ($PSCmdlet.ShouldProcess($TaskName, 'Register 30-minute read-only shadow task (logged-in user only)')) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers `
        -Settings $settings -Principal $principal -Description 'Read-only NDX range forecasts; no orders.'
}
