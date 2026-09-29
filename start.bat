@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-compose.ps1"
if errorlevel 1 (
  echo Startup failed. See the diagnostic message above.
  pause
  exit /b 1
)
pause
