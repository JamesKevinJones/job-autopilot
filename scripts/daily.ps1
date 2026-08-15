# Daily entry point, invoked by the Windows scheduled task at 21:00 IST.
# Runs discovery, then writes the digest to docs/DAILY/<date>.md.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root "data\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$log = Join-Path $logDir ("{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

"[{0}] starting daily run" -f (Get-Date -Format "HH:mm:ss") | Add-Content $log -Encoding utf8

try {
    # Add-Content, not Tee-Object: Tee-Object writes UTF-16 in PowerShell 5.1,
    # which renders the log as spaced-out garbage.
    $output = & (Join-Path $root ".venv\Scripts\python.exe") -m autopilot daily 2>&1
    $output | ForEach-Object { $_.ToString() } | Add-Content $log -Encoding utf8
    $output | ForEach-Object { Write-Output $_ }
    "[{0}] done" -f (Get-Date -Format "HH:mm:ss") | Add-Content $log -Encoding utf8
} catch {
    "[{0}] FAILED: {1}" -f (Get-Date -Format "HH:mm:ss"), $_.Exception.Message | Add-Content $log -Encoding utf8
    throw
}
