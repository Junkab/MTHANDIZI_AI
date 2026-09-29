@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python benchmark.py --checkpoints 307h
pause
