# Append-only runner lifecycle evidence. No environment values/credentials.
function Write-NocturneTaskEvent {
    param([string]$Path, [string]$Event, [hashtable]$Detail = @{})
    $record = @{ At = (Get-Date).ToUniversalTime().ToString('o'); Event = $Event; PID = $PID; Detail = $Detail }
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes(($record | ConvertTo-Json -Compress -Depth 5) + "`n")
    $stream = [IO.FileStream]::new($Path, [IO.FileMode]::Append, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}
