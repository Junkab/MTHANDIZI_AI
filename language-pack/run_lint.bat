@echo off
cd /d "%~dp0"
python tool\lint_pack.py
echo.
echo To check release-readiness (requires everything reviewed):
echo   python tool\lint_pack.py --strict
pause
