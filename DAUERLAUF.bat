@echo off
echo ============================================
echo  Agent — Dauerbetrieb (Ctrl+C zum Stoppen)
echo ============================================
cd /d "%~dp0"
python agent.py --loop
pause
