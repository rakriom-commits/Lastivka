@echo off
REM run_lastivka_log.bat - CMD launcher with logging via PowerShell Tee
setlocal
cd /d C:\Lastivka\lastivka_core

if not exist logs mkdir logs
for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set stamp=%%A
set "LOG=logs\run_%stamp%.txt"

IF EXIST ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) ELSE (
  where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")
)

echo [>] Launching with log: %LOG%
REM Use PowerShell to tee output to both console and file
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Continue'; & %PY% -m main.lastivka 2>&1 | Tee-Object -FilePath '%LOG%'"

echo.
echo [OK] Finished. Log: %LOG%
pause
