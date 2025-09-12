$ErrorActionPreference = "Stop"

$Root    = "C:\Lastivka"
$Core    = "$Root\lastivka_core"
$Logs    = "$Core\logs"
$PidFile = "$Root\temp\lastivka.pid"
$Starter = "$Root\bin\Start-Bridge.ps1"
$State   = "$Logs\watchdog_state.json"
$Log     = "$Logs\watchdog_{0}.log" -f (Get-Date -Format yyyyMMdd)

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Write-Log($msg){
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $Log -Value $line
  if (Test-Path $Log) {
    if ((Get-Item $Log).Length -gt 5MB) {
      $rot = Join-Path $Logs ("watchdog_{0}_{1}.log" -f (Get-Date -Format yyyyMMdd), (Get-Date -Format HHmmss))
      Move-Item -Path $Log -Destination $rot -Force
    }
  }
}

# Стан рестартів
$cfg = @{ WindowSec = 600; MaxRestarts = 3; Restarts = @() }
if (Test-Path $State) {
  try { $cfg = Get-Content $State -Raw | ConvertFrom-Json } catch {}
}
$now = [DateTime]::UtcNow
$cfg.Restarts = @($cfg.Restarts | Where-Object {
  try { ([DateTime]$_) -gt $now.AddSeconds(-1 * $cfg.WindowSec) } catch { $false }
})
function Save-State { ($cfg | ConvertTo-Json -Depth 5) | Set-Content -Path $State -Encoding UTF8 }

# Перевірка процесу
$alive = $false
if (Test-Path $PidFile) {
  try {
    $pid = [int](Get-Content $PidFile -Raw).Trim()
    if (Get-Process -Id $pid -ErrorAction SilentlyContinue) { $alive = $true }
  } catch { $alive = $false }
}

if ($alive) {
  Write-Log "OK: process alive (pid from $PidFile)"
  exit 0
}

if ($cfg.Restarts.Count -ge $cfg.MaxRestarts) {
  Write-Log "HOLD: restart limit reached"
  exit 1
}

try {
  Write-Log "RESTART: running $Starter"
  powershell -NoProfile -ExecutionPolicy Bypass -File $Starter | Out-Null
  $cfg.Restarts += [DateTime]::UtcNow.ToString("o")
  Save-State
  Write-Log "RESTART: done"
  exit 0
} catch {
  Write-Log ("FAIL: restart error: {0}" -f $_.Exception.Message)
  exit 2
}
