@echo off
REM Compiles the workflow engine + tests into a single runnable jar.
REM Requires kotlinc on PATH - see README.md.
cd /d "%~dp0"
if not exist build mkdir build
kotlinc src\main\*.kt src\test\*.kt -include-runtime -d build\workflow-tests.jar
echo Built build\workflow-tests.jar
