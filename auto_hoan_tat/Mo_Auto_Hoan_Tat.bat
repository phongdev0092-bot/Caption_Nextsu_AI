@echo off
cd /d "%~dp0\.."
start "" "http://127.0.0.1:5002"
python -m auto_hoan_tat.run_standalone
pause
