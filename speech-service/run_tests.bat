@echo off
cd /d "%~dp0"
call ..\speech-lab\venv\Scripts\activate.bat
set MTHANDIZI_EAGER_LOAD=false
python -m pytest tests\ -v
pause
