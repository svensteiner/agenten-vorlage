# Reproducible deploy for the automation-agent template (Windows/PowerShell).
# Installs dependencies, validates the project pack, and runs a smoke test.
#
#   scripts\deploy.ps1                 # full deploy with validation
#   scripts\deploy.ps1 -SkipTests      # skip the pytest smoke test
param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> 1/4 Python-Version"
python --version

Write-Host "==> 2/4 Abhaengigkeiten installieren"
python -m pip install -q -r requirements.txt
if (Test-Path requirements-dev.txt) { python -m pip install -q -r requirements-dev.txt }

Write-Host "==> 3/4 Projekt-Pack validieren (tools/check.py)"
# Fail the deploy on any manifest/config error. Not skippable — the gate is the point.
python tools\check.py
if ($LASTEXITCODE -ne 0) { throw "Validierung fehlgeschlagen — Deploy abgebrochen." }

if (-not $SkipTests) {
  Write-Host "==> 4/4 Smoke-Test (pytest)"
  python -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw "Smoke-Test fehlgeschlagen — Deploy abgebrochen." }
} else {
  Write-Host "==> 4/4 Smoke-Test uebersprungen (-SkipTests)"
}

Write-Host "OK Deploy-Pruefung abgeschlossen. Start mit: python agent.py"
