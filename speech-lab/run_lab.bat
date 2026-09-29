@echo off
REM MTHANDIZI Speech Lab - Windows launcher
cd /d "%~dp0"
if not exist venv\Scripts\activate.bat (
  echo No venv found. Run setup first - see README.md
  pause & exit /b 1
)
call venv\Scripts\activate.bat
echo Starting MTHANDIZI Speech Lab on http://localhost:8077
python lab_server.py
pause
