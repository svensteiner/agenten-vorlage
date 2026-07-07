@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo.
echo  Doppelklick reicht — wir fragen alles was benoetigt wird.
echo.

REM Python finden: erst der Windows-Launcher 'py', dann 'python' im PATH.
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
    echo  [Fehler] Python wurde nicht gefunden.
    echo  Bitte Python 3.10 oder neuer installieren: https://www.python.org/downloads/
    echo  Wichtig: beim Setup das Haekchen "Add Python to PATH" setzen.
    echo.
    pause
    exit /b 1
)

%PYCMD% agent_cli.py setup
echo.
pause
