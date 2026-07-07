@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ============================================
echo  Agent — Dauerbetrieb (Ctrl+C zum Stoppen)
echo ============================================

REM Python finden: erst der Windows-Launcher 'py', dann 'python' im PATH.
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
    where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
    echo  [Fehler] Python wurde nicht gefunden. Bitte zuerst SETUP.bat ausfuehren.
    echo  Download: https://www.python.org/downloads/  (Haekchen "Add Python to PATH" setzen)
    echo.
    pause
    exit /b 1
)

%PYCMD% agent.py --loop
pause
