@echo off
REM Same as run_service.bat but loads the model on first request instead of at
REM startup - faster to launch during development, wrong for the real kiosk
REM (first citizen shouldn't wait ~2 minutes). Use run_service.bat for anything
REM resembling a real demo or deployment.
cd /d "%~dp0"
call ..\speech-lab\venv\Scripts\activate.bat
set MTHANDIZI_EAGER_LOAD=false
python -m app.main
pause
