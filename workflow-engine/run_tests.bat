@echo off
REM Must be run from this directory - tests load real JSON files via services\*.json
cd /d "%~dp0"
if not exist build\workflow-tests.jar (
  echo No build found - running build.bat first
  call build.bat
)
java -cp build\workflow-tests.jar mthandizi.workflow.test.RunTestsKt
