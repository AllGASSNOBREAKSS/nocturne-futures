[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Python = (Get-Command python -ErrorAction Stop).Source,
    [string]$Repository,
    [string]$TaskName = 'Nocturne-ReadOnly-Research',
    [ValidateRange(1,24)][int]$CadenceHours = 6,
    [ValidateSet('Interactive', 'Password')][string]$LogonMode = 'Interactive',
    [PSCredential]$Credential,
    [switch]$WakeToRun
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
$Python = (Resolve-Path $Python).Path
$Repository = (Resolve-Path $Repository).Path
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Task exists; inspect before changing it: $TaskName"
}
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($LogonMode -eq 'Password' -and $Credential) { $user = $Credential.UserName }
if ($LogonMode -eq 'Password' -and -not $Credential -and -not $WhatIfPreference) {
    throw 'Unattended mode requires an explicitly supplied PSCredential; no password argument or stored plaintext is accepted.'
}
$runner = Join-Path $Repository 'scripts/run_headless_task.py'
$PythonWindowless = Join-Path (Split-Path $Python -Parent) 'pythonw.exe'
if (-not (Test-Path $PythonWindowless)) { throw 'A matching pythonw.exe is required for console-free scheduled operation.' }
$action = New-ScheduledTaskAction -Execute $PythonWindowless -WorkingDirectory $Repository -Argument (
    '"{0}" --lane research --python "{1}" --repository "{2}"' -f $runner,$Python,$Repository
)
$triggers = @((New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours $CadenceHours)))
if ($LogonMode -eq 'Password') { $triggers += New-ScheduledTaskTrigger -AtStartup }
else { $triggers += New-ScheduledTaskTrigger -AtLogOn -User $user }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 18) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun:$WakeToRun
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType $LogonMode -RunLevel Limited
if ($PSCmdlet.ShouldProcess($TaskName, 'Register bounded research-only task; existing shadow task unchanged')) {
    $task = New-ScheduledTask -Action $action -Trigger $triggers `
        -Settings $settings -Principal $principal -Description 'Bounded research only; no trading, no automatic promotion.'
    if ($LogonMode -eq 'Password') {
        try {
            $password = $Credential.GetNetworkCredential().Password
            Register-ScheduledTask -TaskName $TaskName -InputObject $task -User $user -Password $password
        } finally { $password = $null }
    } else { Register-ScheduledTask -TaskName $TaskName -InputObject $task }
}
