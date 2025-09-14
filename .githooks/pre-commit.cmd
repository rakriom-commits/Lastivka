@echo off
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tools\Clean-Caches.ps1" -Root "%CD%"
exit /B 0
