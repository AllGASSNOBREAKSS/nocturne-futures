# Installs Nocturne Terminal for the current user (no admin rights needed).
# Copies the packaged app to %LOCALAPPDATA%\Programs\Nocturne Terminal, writes
# nocturne.json (repo + Python paths) and creates Desktop and Start Menu shortcuts.
param(
    [string]$Repo = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$Python = (Get-Command python -ErrorAction Stop).Source
)
$ErrorActionPreference = "Stop"
$source = Join-Path $Repo "desktop\release\win-unpacked"
if (-not (Test-Path (Join-Path $source "Nocturne Terminal.exe"))) { throw "Build first: cd desktop; npm run build; npx electron-builder --win dir" }
$target = Join-Path $env:LOCALAPPDATA "Programs\Nocturne Terminal"
Get-Process "Nocturne Terminal" -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path $target) { Remove-Item $target -Recurse -Force }
Copy-Item $source $target -Recurse
@{ repo = $Repo; python = $Python } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $target "nocturne.json")
$exe = Join-Path $target "Nocturne Terminal.exe"
$icon = Join-Path $target "nocturne.ico"
Copy-Item (Join-Path $Repo "desktop\electron\icon.ico") $icon
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath("Desktop"), (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"))) {
    $link = $shell.CreateShortcut((Join-Path $folder "Nocturne Terminal.lnk"))
    $link.TargetPath = $exe
    $link.WorkingDirectory = $target
    $link.IconLocation = "$icon,0"
    $link.Description = "Nocturne Futures research terminal (historical research; NO_TRADE)"
    $link.Save()
}
Write-Output "Installed to $target (repo: $Repo, python: $Python)"
