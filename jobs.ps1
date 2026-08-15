# Run the autopilot from anywhere:
#   & "C:\Users\kj638\Kevin codes\job-autopilot\jobs.ps1" queue
#
# `python -m autopilot` only works from the project root, because that is
# where the `autopilot` package lives. This wrapper handles the location for
# you and restores your previous directory afterwards.

param([Parameter(ValueFromRemainingArguments = $true)] $Args)

$root = $PSScriptRoot
# Always use the project venv. The bare `python` on PATH resolves to the
# Claude agent's venv, which has no pip and none of this project's
# dependencies installed.
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing venv. Create it with:  py -3.14 -m venv .venv"
    exit 1
}

Push-Location $root
try {
    if (-not $Args) { $Args = @("queue") }
    & $py -m autopilot @Args
} finally {
    Pop-Location
}
