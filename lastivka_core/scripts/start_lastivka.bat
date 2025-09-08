@echo off
setlocal
pushd "%~dp0.."
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "Start-Lastivka.ps1"
popd
endlocal
