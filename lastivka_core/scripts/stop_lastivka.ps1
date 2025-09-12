param(
  [string]$Root = "C:\Lastivka",
  [int]$TimeoutSec = 5
)

$ErrorActionPreference = "Stop"

# зняти підписники подій Lastivka*
Get-EventSubscriber |
  ? { $_.SourceIdentifier -like 'LastivkaBridge*' -or $_.SourceIdentifier -like 'LastivkaWatcher*' } |
  Unregister-Event -ErrorAction SilentlyContinue
Get-Event | Remove-Event -ErrorAction SilentlyContinue

# якщо є pidfile — прибиваємо саме цей екземпляр
$pidf = Join-Path $Root 'temp\lastivka.pid'
if (Test-Path -LiteralPath $pidf) {
  $procIdTxt = (Get-Content -LiteralPath $pidf -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if ($procIdTxt -match '^\d+$') {
    $procId = [int]$procIdTxt
    try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch { & taskkill /PID $procId /T /F | Out-Null }
    try { Wait-Process -Id $procId -Timeout $TimeoutSec -ErrorAction SilentlyContinue } catch {}
  }
}

# стоп містка (PS-процеси з Start-Bridge.ps1)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  ? { $_.Name -match '^pwsh(\.exe)?$|^powershell(\.exe)?$' -and ($_.CommandLine -match 'Start-Bridge\.ps1') } |
  % { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }

# стоп ядра (python/pythonw/py/pyw з нашим модулем)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  ? {
      $_.Name -match '^python(w)?(\.exe)?$|^py(w)?(\.exe)?$' -and
      ($_.CommandLine -match '(-m|\s)lastivka_core(\.main)?\.lastivka(\s|$)|lastivka_core\\main\\lastivka\.py')
    } |
  % { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }

# прибрати лок-файл
if (Test-Path -LiteralPath $pidf) { Remove-Item -LiteralPath $pidf -Force -ErrorAction SilentlyContinue }

Write-Host '[lastivka] Stop requested -> done.'
