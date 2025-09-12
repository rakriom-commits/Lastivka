Get-Process WerFault -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
