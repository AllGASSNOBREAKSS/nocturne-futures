[CmdletBinding()]
param(
    [switch]$Exercise,
    [ValidateRange(1,5)][int]$Repetitions = 2,
    [ValidateRange(30,300)][int]$TimeoutSeconds = 150,
    [string]$Repository,
    [ValidatePattern('^[A-Za-z0-9_-]+\.json$')][string]$ReportName = 'phase3q_scheduler.json'
)
$ErrorActionPreference = 'Stop'
if (-not $Repository) { $Repository = Split-Path $PSScriptRoot -Parent }
$names = @('Nocturne-NDX-ReadOnly-Shadow', 'Nocturne-ReadOnly-Research')
$observations = @()
$count = 1
if ($Exercise) { $count = $Repetitions }
for ($attempt = 1; $attempt -le $count; $attempt++) {
    if ($Exercise) {
        foreach ($name in $names) { Start-ScheduledTask -TaskName $name }
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        do {
            Start-Sleep -Seconds 2
            $running = @(Get-ScheduledTask -TaskName $names | Where-Object State -eq 'Running')
        } while ($running.Count -gt 0 -and (Get-Date) -lt $deadline)
    }
    foreach ($name in $names) {
        $task = Get-ScheduledTask -TaskName $name
        $info = $task | Get-ScheduledTaskInfo
        $directory = 'data/shadow/task-logs'
        if ($name -eq 'Nocturne-ReadOnly-Research') { $directory = 'data/research/orchestrator/task-logs' }
        $receipt = Get-ChildItem (Join-Path $Repository "$directory/*-events.jsonl") -ErrorAction SilentlyContinue |
            Where-Object LastWriteTime -ge $info.LastRunTime.AddSeconds(-2) | Sort-Object Name -Descending | Select-Object -First 1
        $events = @()
        if ($receipt) { $events = @(Get-Content $receipt.FullName | ForEach-Object { $_ | ConvertFrom-Json }) }
        $finished = @($events | Where-Object Event -eq 'RUN_FINISHED')
        $complete = $finished.Count -eq 1 -and $finished[0].Detail.ExitCode -eq $info.LastTaskResult
        $launcher = Get-ChildItem (Join-Path $Repository "$directory/*-launcher.jsonl") -ErrorAction SilentlyContinue |
            Where-Object LastWriteTime -ge $info.LastRunTime.AddSeconds(-2) | Sort-Object Name -Descending | Select-Object -First 1
        $launcherEvents = @()
        if ($launcher) { $launcherEvents = @(Get-Content $launcher.FullName | ForEach-Object { $_ | ConvertFrom-Json }) }
        $launcherFinished = @($launcherEvents | Where-Object event -eq 'LAUNCHER_FINISHED')
        $launcherComplete = $launcherFinished.Count -eq 1 -and $launcherFinished[0].exit_code -eq $info.LastTaskResult
        if ($task.Actions[0].Execute.EndsWith('pythonw.exe')) { $complete = $complete -and $launcherComplete }
        $observations += @{
            ObservedAt = (Get-Date).ToUniversalTime().ToString('o'); Attempt = $attempt; Name = $name
            State = [string]$task.State; LastRun = $info.LastRunTime.ToUniversalTime().ToString('o')
            NextRun = $info.NextRunTime.ToUniversalTime().ToString('o'); ExitCode = $info.LastTaskResult
            LogonType = [string]$task.Principal.LogonType; WindowlessLauncher = $task.Actions[0].Execute.EndsWith('pythonw.exe')
            CompleteLifecycleReceipt = $complete; Events = $events; LauncherEvents = $launcherEvents
        }
    }
}
$bad = @($observations | Where-Object { $_.ExitCode -ne 0 -or $_.State -ne 'Ready' -or -not $_.CompleteLifecycleReceipt })
$status = 'LAST_OBSERVED_COMPLETIONS_OK'
if ($bad.Count -gt 0) { $status = 'DEGRADED' }
$report = @{ GeneratedAt = (Get-Date).ToUniversalTime().ToString('o'); Status = $status; Exercised = [bool]$Exercise
    Observations = $observations; Limitations = 'Awake interactive host only; no reboot/logoff, soak, off-host paging or 24/7 claim.' }
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Repository "reports/$ReportName")
Write-Output ($report | ConvertTo-Json -Compress -Depth 8)
if ($bad.Count -gt 0) { exit 1 }
