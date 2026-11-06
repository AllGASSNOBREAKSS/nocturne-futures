# Append-only runner lifecycle evidence. No environment values/credentials.
function Write-NocturneTaskEvent {
    param([string]$Path, [string]$Event, [hashtable]$Detail = @{})
    $record = @{ At = (Get-Date).ToUniversalTime().ToString('o'); Event = $Event; PID = $PID; Detail = $Detail }
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($record | ConvertTo-Json -Compress -Depth 5) + "`n")
    $stream = [IO.FileStream]::new($Path, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

function Open-NocturneTaskGuard {
    param([string]$Path, [string]$Events, [int]$MaintenanceWaitSeconds = 45)
    $deadline = (Get-Date).AddSeconds($MaintenanceWaitSeconds)
    $announced = $false
    while ($true) {
        try {
            return [IO.File]::Open($Path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        } catch [IO.IOException] {
            # Another wrapper owns a deny-share handle: fail BUSY immediately.
            # A cooperative backup uses a shared OS byte lock: it allows this
            # probe to open, so wait boundedly without touching its locked byte.
            $probe = $null
            try { $probe = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite) }
            catch [IO.IOException] { throw }
            finally { if ($probe) { $probe.Dispose() } }
            if ((Get-Date) -ge $deadline) { throw [IO.IOException]::new('Maintenance guard wait budget exhausted') }
            if (-not $announced) {
                Write-NocturneTaskEvent $Events 'MAINTENANCE_WAIT' @{ LimitSeconds = $MaintenanceWaitSeconds }
                $announced = $true
            }
            Start-Sleep -Milliseconds 250
        }
    }
}
