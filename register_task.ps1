# register_task.ps1 — Registriert den Agenten als Windows Task Scheduler Aufgabe
#
# Führt aus: python agent.py --loop  beim Windows-Login
# Startet neu wenn der Prozess abstürzt (3 Versuche, 1 Minute Pause)
#
# Ausführen als Administrator:
#   powershell -ExecutionPolicy Bypass -File register_task.ps1

param(
    [string]$TaskName = "Agent-Dauerlauf",
    [string]$PythonExe = ""
)

# Python-Pfad automatisch ermitteln
if (-not $PythonExe) {
    $candidates = @(
        "C:\Program Files\Python313\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue)?.Source
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { $PythonExe = $c; break }
    }
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Error "Python nicht gefunden. Pfad mit -PythonExe angeben."
    exit 1
}

$ScriptDir  = $PSScriptRoot
$ScriptPath = Join-Path $ScriptDir "agent.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "agent.py nicht gefunden in: $ScriptDir"
    exit 1
}

Write-Host "=== Agent Task Scheduler Registrierung ===" -ForegroundColor Cyan
Write-Host "  Task-Name  : $TaskName"
Write-Host "  Python     : $PythonExe"
Write-Host "  Script     : $ScriptPath"
Write-Host "  Arbeitsverz: $ScriptDir"
Write-Host ""

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-u agent.py --loop" `
    -WorkingDirectory $ScriptDir

# Beim Login starten
$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit "00:00:00" `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -RunLevel Highest `
    -LogonType Interactive

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null

    Write-Host "✅ Task '$TaskName' erfolgreich registriert." -ForegroundColor Green
    Write-Host ""
    Write-Host "Befehle:" -ForegroundColor Yellow
    Write-Host "  Starten : Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Stoppen : Stop-ScheduledTask  -TaskName '$TaskName'"
    Write-Host "  Entfernen: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
    Write-Host ""
    Write-Host "Der Agent startet automatisch beim nächsten Windows-Login." -ForegroundColor Cyan

} catch {
    Write-Error "Fehler bei Registrierung: $_"
    Write-Host "Tipp: Skript als Administrator ausführen." -ForegroundColor Yellow
    exit 1
}
