# Закрити саме той python, що запущений як "-m main.lastivka"
$px = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -match '\-m\s+main\.lastivka' }
$px | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Прибрати PID-замок
Remove-Item "C:\Lastivka\lastivka_core\temp\lastivka.pid" -Force -ErrorAction SilentlyContinue
Write-Host "Готово. Можна запускати місток знову."
