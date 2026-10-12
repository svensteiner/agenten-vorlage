[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [string]$Workspace = (Join-Path $PSScriptRoot "agents\programming-agent\workspace"),
    [ValidateSet("codex", "deepseek", "api", "anthropic")]
    [string]$Backend = "codex",
    [ValidateNotNullOrEmpty()]
    [ValidateScript({ -not [string]::IsNullOrWhiteSpace($_) })]
    [string]$Task = "Analysiere den Workspace und nenne zuerst Ziel, relevante Architektur, vorhandene Tests und Risiken. Implementiere danach nur die kleinste vollstaendige Aenderung, teste sie mit frischer Evidenz und lasse das Ergebnis durch eine separate read-only Rolle pruefen. Bewahre fremde Aenderungen und fuehre kein Deployment aus."
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $Root "Start-AI-Studio.ps1") `
    -Port $Port `
    -DefaultWorkspace $Workspace `
    -PreferredAgent "programming-agent" `
    -PreferredBackend $Backend `
    -StarterTask $Task `
    -OpenBrowser
exit $LASTEXITCODE
