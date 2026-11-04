[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [string]$Repository,
    [string]$TaskName = 'Nocturne-NDX-ReadOnly-Shadow',
    [ValidateSet('Interactive', 'Password')][string]$LogonMode = 'Interactive',
    [PSCredential]$Credential,
    [switch]$WakeToRun
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
$Python = (Resolve-Path $Python).Path
$Repository = (Resolve-Path $Repository).Path
$runner = Join-Path $Repository 'scripts/run_shadow_task.ps1'
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($LogonMode -eq 'Password' -and $Credential) { $user = $Credential.UserName }
if ($LogonMode -eq 'Password' -and -not $Credential -and -not $WhatIfPreference) {
    throw 'Unattended mode needs an explicitly supplied PSCredential; use Get-Credential interactively. No password CLI argument is accepted.'
}
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $Repository -Argument (
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Python "{1}" -Repository "{2}"' -f $runner, $Python, $Repository
)
$triggers = @((New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)))
if ($LogonMode -eq 'Password') { $triggers += New-ScheduledTaskTrigger -AtStartup }
else { $triggers += New-ScheduledTaskTrigger -AtLogOn -User $user }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun:$WakeToRun
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType $LogonMode -RunLevel Limited
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Task already exists; inspect it before changing or removing it: $TaskName"
}
if ($PSCmdlet.ShouldProcess($TaskName, "Register 30-minute read-only shadow task ($LogonMode logon)")) {
    $task = New-ScheduledTask -Action $action -Trigger $triggers -Settings $settings `
        -Principal $principal -Description 'Read-only NDX range forecasts; no orders.'
    if ($LogonMode -eq 'Password') {
        # Windows Task Scheduler protects the credential. Never write it into
        # task arguments, files, environment variables or diagnostic output.
        try {
            $password = $Credential.GetNetworkCredential().Password
            Register-ScheduledTask -TaskName $TaskName -InputObject $task -User $user -Password $password
        } finally { $password = $null }
    } else {
        Register-ScheduledTask -TaskName $TaskName -InputObject $task
    }
}
