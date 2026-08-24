@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
    echo  [Fehler] Python wurde nicht gefunden. Bitte zuerst SETUP.bat ausfuehren.
    echo.
    pause
    exit /b 1
)

%PYCMD% -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [Fehler] Die kostenlose Excel-Unterstuetzung fehlt.
    echo  Einmalig bewusst ausfuehren:
    echo  %PYCMD% -m pip install -r requirements-demo.txt
    echo  Der Demo-Start selbst installiert nichts und bleibt offline.
    echo.
    pause
    exit /b 1
)

echo.
echo  KMU-Mietportal startet lokal. Oben: Agenten mieten.
echo  Darunter: kostenlose 0-Euro-Demo. Keine LLM-, Azure- oder Zahlungskosten.
echo  Zum Beenden dieses Fenster schliessen oder Strg+C druecken.
echo.
%PYCMD% order_portal.py
pause
