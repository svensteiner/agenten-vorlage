@echo off
chcp 65001 >nul
echo.
echo  Doppelklick reicht — wir fragen alles was benoetigt wird.
echo.
cd /d "%~dp0"
python agent_cli.py setup
echo.
pause
