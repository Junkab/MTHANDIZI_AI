@echo off
REM MTHANDIZI Speech Service - Windows launcher
REM Uses the SAME venv as speech-lab (this service imports speech-lab's lab/
REM package directly - see app/config.py for why). No separate install needed;
REM if speech-lab's venv works, this works.
cd /d "%~dp0"
if not exist ..\speech-lab\venv\Scripts\activate.bat (
  echo Could not find ..\speech-lab\venv - set up speech-lab first, see its README.md
  pause & exit /b 1
)
call ..\speech-lab\venv\Scripts\activate.bat
echo Starting MTHANDIZI Speech Service on http://0.0.0.0:8090
echo Other devices on this network can reach it at http://YOUR-LAN-IP:8090
echo Press Ctrl+C to stop.
python -m app.main
pause
