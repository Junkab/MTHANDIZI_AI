@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python tts_case_test.py
pause
