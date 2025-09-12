<# Start-Bridge.ps1 — тихий старт Lastivka ядра через pyw.exe
   Функції:
   • single-instance через C:\Lastivka\temp\lastivka.pid
   • запуск без миготіння (pyw.exe)
   • лог stdout/stderr у C:\Lastivka\logs\
   • акуратна перевірка живості процесу
#>

param(
  [string]$Root   = "C:\Lastivka",
  [string]$Module = "lastivka_core.main.lastivka"
)

$ErrorActionPreference = "Stop"

# -- Paths
$Temp   = Join-Path $Root "temp"
$Logs   = Join-Path $Root "logs"
$Pid    = Join-Path $Temp "lastivka.pid"

New-Item -ItemType Directory -Force -Path $Temp,$Logs | Out-Null

function Get-PywPath {
  # Пріоритет: %WINDIR%\pyw.exe → pythonw.exe з PATH → pythonw.exe з WindowsApps
  $candidates = @(
    (Join-Path $env:WinDir "pyw.exe"),
    "pythonw.exe",
    (Join-Path $env:LocalAppData "Microsoft\WindowsApps\pythonw.exe")
  )
  foreach ($c in $candidates) {
    try { $cmd = Get-Command $c -ErrorAction Stop; return $cmd.Source } catch {}
  }
  throw "Не знайдено pyw.exe/pythonw.exe у системі."
}

function Is-Alive([int]$pid) {
  try { $p = Get-Process -Id $pid -ErrorAction Stop; return -not $p.HasExited } catch { return $false }
}

# -- Single instance
if (Test-Path $Pid) {
  $old = (Get-Content $Pid -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if ($old -match '^\d+$' -and (Is-Alive([int]$old))) {
    Write-Host "Lastivka вже запущена (PID $old). Вихід."
    exit 0
  }
  # застарілий PID — прибираємо
  Remove-Item $Pid -ErrorAction SilentlyContinue
}

# -- Build start
$pyw = Get-PywPath
$ts  = Get-Date -Format 'yyyyMMdd_HHmmss'
$stdout = Join-Path $Logs ("bridge_stdout_{0}.txt" -f $ts)
$stderr = Join-Path $Logs ("bridge_stderr_{0}.txt" -f $ts)
$args   = @("-3","-u","-m",$Module)

# -- Start hidden
$proc = Start-Process -FilePath $pyw -ArgumentList $args `
  -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $stdout -RedirectStandardError $stderr

# -- Persist PID
$proc.Id | Out-File -FilePath $Pid -Encoding ascii -Force

# -- Quick health check
Start-Sleep -Milliseconds 400
if (-not (Is-Alive($proc.Id))) {
  $msg = "Процес впав одразу після старту. Дивись лог: $stderr"
  # чистимо pid
  Remove-Item $Pid -ErrorAction SilentlyContinue
  throw $msg
}

Write-Host "Lastivka стартувала (PID $($proc.Id)). Логи: $stdout ; $stderr"
exit 0
