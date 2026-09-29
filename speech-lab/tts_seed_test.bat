@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python tts_seed_test.py
pause
