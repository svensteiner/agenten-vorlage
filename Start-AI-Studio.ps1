[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765
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
    Write-Error "AgentKit dependencies are missing for $Python. Create/use .venv and run 'python -m pip install -e .' manually; this launcher does not install dependencies."
    exit 1
}
& $Python (Join-Path $Root "cockpit\server.py") --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
