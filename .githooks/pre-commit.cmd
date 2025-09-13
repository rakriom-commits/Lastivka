@echo off
setlocal

echo [Pre-commit] Start Clean-Caches.ps1...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Clean-Caches.ps1"
if errorlevel 1 (
  echo [Pre-commit] ERROR: Clean-Caches.ps1 failed.
  exit /b 1
)

echo [Pre-commit] OK: caches cleaned.
endlocal
exit /b 0