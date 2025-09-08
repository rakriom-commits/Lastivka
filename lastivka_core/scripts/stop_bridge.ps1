# stop_bridge.ps1 — чиста зупинка містка
Get-EventSubscriber | ? {$_.SourceIdentifier -like 'LastivkaBridge*'} | Unregister-Event -ErrorAction SilentlyContinue
Get-Event | Remove-Event -ErrorAction SilentlyContinue

$pidf = 'C:\Lastivka\temp\lastivka.pid'
if (Test-Path -LiteralPath $pidf) {
  Remove-Item -LiteralPath $pidf -Force -ErrorAction SilentlyContinue
}

(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | ? { $_.CommandLine -match 'Start-Bridge\.ps1' }) |
  % { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }

Write-Host '[bridge] Stop requested.'
