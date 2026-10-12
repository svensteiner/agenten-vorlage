[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [string]$DefaultWorkspace = "",
    [string]$PreferredAgent = "",
    [ValidateSet("", "demo", "codex", "deepseek", "api", "anthropic")]
    [string]$PreferredBackend = "",
    [string]$StarterTask = "",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $Python = $venvPython
} else {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        Write-Error "Python 3.11+ was not found. Install Python and ensure 'python' is on PATH. Dependencies are not installed automatically."
        exit 1
    }
    $Python = $command.Source
}

& $Python -c "import sys, yaml, jsonschema, pypdf, defusedxml, pytest; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "AgentKit dependencies are missing for $Python. Create/use .venv and run: python -m pip install -e '.[execution]'. This launcher does not install dependencies."
    exit 1
}
$serverArguments = @(
    (Join-Path $Root "cockpit\server.py"),
    "--host", "127.0.0.1",
    "--port", "$Port"
)
if ($DefaultWorkspace) {
    if (-not (Test-Path -LiteralPath $DefaultWorkspace -PathType Container)) {
        Write-Error "Workspace does not exist: $DefaultWorkspace"
        exit 1
    }
    $serverArguments += @("--default-workspace", $DefaultWorkspace)
}
if ($PreferredAgent) {
    $serverArguments += @("--preferred-agent", $PreferredAgent)
}
if ($PreferredBackend) {
    $serverArguments += @("--preferred-backend", $PreferredBackend)
}
if ($StarterTask) {
    $serverArguments += @("--starter-task", $StarterTask)
}
if ($OpenBrowser) {
    $serverArguments += "--open-browser"
}
& $Python @serverArguments
exit $LASTEXITCODE
