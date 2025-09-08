# stop_lastivka.ps1  зупинка ядра + містка, очистка PID
Get-EventSubscriber | ? {$_.SourceIdentifier -like 'LastivkaBridge*'} | Unregister-Event -ErrorAction SilentlyContinue
Get-Event | Remove-Event -ErrorAction SilentlyContinue

# стоп містка (якщо є)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  ? { $_.CommandLine -match 'Start-Bridge\.ps1' } |
  % { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# стоп ядра (python -m lastivka_core.main.lastivka)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  ? { $_.Name -match '^python(\.exe)?$' -and ($_.CommandLine -match '(-m|\s)lastivka_core(\.main)?\.lastivka(\s|$)|lastivka_core\\main\\lastivka\.py') } |
  % { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# прибрати лок-файл
$pidf='C:\Lastivka\temp\lastivka.pid'
if (Test-Path -LiteralPath $pidf){ Remove-Item -LiteralPath $pidf -Force -ErrorAction SilentlyContinue }

Write-Host '[lastivka] Stop requested.'
