# watchdog_wrapper.ps1 — ping & restart bridge/core for Lastivka (PS 5.1)
$Root    = "C:\Lastivka"
$PidFile = Join-Path $Root "temp\lastivka.pid"

# логування
$LogDir = Join-Path $Root "lastivka_core\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("watchdog_{0:yyyyMMdd}.log" -f (Get-Date))
function Log($m){ "[{0:yyyy-MM-dd HH:mm:ss}] $m" -f (Get-Date) | Out-File $Log -Append -Encoding utf8 }

# 1) якщо ядро живе — OK і вихід (без «alive»-спаму)
try {
  if (Test-Path $PidFile) {
    $BridgePid = [int](Get-Content $PidFile -Raw)
    $p   = Get-Process -Id $BridgePid -ErrorAction SilentlyContinue
    if ($p) {
      $cmdObj = Get-CimInstance Win32_Process -Filter "ProcessId=$BridgePid" -ErrorAction SilentlyContinue
      $cmd    = $cmdObj.CommandLine
      $nameOk = ($p.ProcessName -match '^py(w)?$|^python(w)?$' -or $p.ProcessName -match '^py$')
      $sigOk  = ($cmd -and ($cmd -match '(-m|\s)lastivka_core(\.main)?\.lastivka(\s|$)|lastivka_core\\main\\lastivka\.py'))
      if ($nameOk -and ($sigOk -or -not $cmd)) { exit 0 }
    }
  }
} catch {}

# 2) спроба підняти міст через Start-Bridge.ps1
try {
  $oldPid = $null
  if (Test-Path $PidFile) { $oldPid = [int](Get-Content $PidFile -Raw) }

  & "C:\Lastivka\lastivka_core\Start-Bridge.ps1" | Out-Null
  Start-Sleep -Milliseconds 1200

  if (Test-Path $PidFile) {
    $newPid = [int](Get-Content $PidFile -Raw)
    $p = Get-Process -Id $newPid -ErrorAction SilentlyContinue
    if ($p) {
      if ($oldPid -and $newPid -eq $oldPid) { Log "OK: already running, PID=$newPid" }
      else { Log "OK: restarted, PID=$newPid" }
      exit 0
    }
  }
} catch {
  Log "ERROR(Start-Bridge): $($_.Exception.Message)"
}

# 3) Fallback: прямий запуск pythonw/pyw
try {
  $err = Join-Path $LogDir ("bridge_stderr_{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))
  $out = Join-Path $LogDir ("bridge_stdout_{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))

  function _GetPyw {
    foreach ($c in @("$env:WINDIR\pyw.exe","pythonw.exe","$env:LocalAppData\Microsoft\WindowsApps\pythonw.exe")) {
      try { $cmd = Get-Command $c -ErrorAction Stop; return $cmd.Source } catch {}
    }
    return $null
  }

  $pyw = _GetPyw
  if (-not $pyw) { throw "pyw/pythonw not found" }

  $p = Start-Process -FilePath $pyw -ArgumentList "-3 -u -m lastivka_core.main.lastivka" `
        -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
        -RedirectStandardError $err -RedirectStandardOutput $out

  $p.Id | Out-File -FilePath $PidFile -Encoding ascii
  Start-Sleep -Milliseconds 1200

  $alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if ($alive) { Log "OK: fallback started, PID=$($p.Id)"; exit 0 } else { Log "ERROR: fallback died, see $err" }
} catch {
  Log "ERROR(Fallback): $($_.Exception.Message)"
}

exit 0
