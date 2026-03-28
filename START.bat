@echo off
echo ============================================
echo  Agent starten — einmaliger Lauf
echo ============================================
cd /d "%~dp0"
python agent.py %*
pause
