[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [string]$MarketingbotPath = "C:\Users\botrunner\projects\marketingbot"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $Python = $venvPython
} else {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        Write-Error "Python 3.11+ was not found."
        exit 1
    }
    $Python = $command.Source
}
$Snapshot = & $Python `
    (Join-Path $Root "agentkit\marketing_snapshot.py") `
    --source $MarketingbotPath `
    --output-root (Join-Path $Root "cockpit\.runs\marketing-snapshots")
if ($LASTEXITCODE -ne 0 -or -not $Snapshot) {
    Write-Error "The safe Marketingbot snapshot could not be created."
    exit 1
}
$Snapshot = [string]($Snapshot | Select-Object -Last 1)
Write-Host "Kuratierter Marketing-Snapshot: $Snapshot"
$Task = "Analysiere den aktuellen Marketingbot-Livezustand read-only. Nutze nur verifizierte eigene Outcomes und benenne Messluecken. Erstelle danach genau einen priorisierten, reversiblen 7-Tage-Plan zur deutlichen Steigerung der qualifizierten X-Sichtbarkeit mit Baseline, Zielmetrik, Mindeststichprobe, Stopregel und naechstem Review. Starte keinen Prozess und fuehre keine Live-X-Aktion aus."

& (Join-Path $Root "Start-AI-Studio.ps1") `
    -Port $Port `
    -DefaultWorkspace $Snapshot `
    -PreferredAgent "x-growth-agent" `
    -PreferredBackend "codex" `
    -StarterTask $Task `
    -OpenBrowser
exit $LASTEXITCODE
