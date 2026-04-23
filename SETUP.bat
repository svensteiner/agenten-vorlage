@echo off
echo ============================================
echo  Agent Setup Wizard
echo ============================================
cd /d "%~dp0"
python agent_cli.py setup
pause
