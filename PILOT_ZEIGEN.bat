@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ===========================================================
REM  Pilot-Demo vorfuehren - Muster Bau GmbH
REM  Startet einen lokalen Webserver und oeffnet den Browser.
REM  Nichts geht ins Internet. Keine LLM- oder Cloud-Kosten.
REM  Beenden: dieses Fenster schliessen oder Strg+C.
REM ===========================================================

set "PORT=8777"

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
    echo.
    echo  [Fehler] Python wurde nicht gefunden. Bitte zuerst SETUP.bat ausfuehren.
    echo  Download: https://www.python.org/downloads/  ^(Haekchen "Add Python to PATH" setzen^)
    echo.
    pause
    exit /b 1
)

if not exist "prototype\index.html" (
    echo.
    echo  [Fehler] prototype\index.html nicht gefunden.
    echo  Der Projektordner ist unvollstaendig oder wurde verschoben.
    echo.
    pause
    exit /b 1
)

echo.
echo   Ablauf der Vorfuehrung ^(20 Minuten^):
echo     1. Firmenkarte oben zeigen - Muster Bau GmbH, Augsburg
echo     2. Knopf "Gefuehrte Demo" druecken und laufen lassen
echo     3. Bei jeder Antwort auf einen Beleg klicken ^(Quelle + Pfad^)
echo     4. Finale: "Agent dazubuchen" - das ist der Abo-Moment
echo.
echo   Ausfuehrlich: PILOT_VORFUEHRUNG.md

REM Der Starter oeffnet den Browser erst, wenn der Server wirklich antwortet,
REM und weicht auf den naechsten freien Port aus, falls 8777 belegt ist.
%PYCMD% scripts\serve_pilot.py %PORT%

if errorlevel 1 (
    echo.
    echo  Die Demo wurde mit einem Fehler beendet ^(siehe Meldung oben^).
    pause
)
