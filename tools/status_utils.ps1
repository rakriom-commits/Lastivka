function Get-LastivkaStatus {
  $Root="C:\Lastivka"
  $PidFile=Join-Path $Root "temp\lastivka.pid"
  $log = Join-Path $Root ("lastivka_core\logs\watchdog_{0:yyyyMMdd}.log" -f (Get-Date))
  $status = [ordered]@{}
  $status.PidFile = (Test-Path $PidFile)
  if ($status.PidFile) {
    $procId = [int](Get-Content $PidFile -Raw)
    $status.PID = $procId
    $p = Get-Process -Id $procId -EA SilentlyContinue
    $status.Process = if ($p) { $p.ProcessName } else { "<dead>" }
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -EA SilentlyContinue).CommandLine
    $status.Cmdline = $cmd
  }
  $status.WatchdogLogExists = Test-Path $log
  $status.WatchdogLogTail   = if (Test-Path $log) { (Get-Content $log -Tail 5) -join "`n" } else { "<no log today>" }
  [pscustomobject]$status
}

function Start-Lastivka {
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass `
    -File "C:\Lastivka\lastivka_core\security\watchdog_wrapper.ps1" | Out-Null
  Start-Sleep -Milliseconds 800
  Get-LastivkaStatus
}

function Stop-Lastivka {
  & "C:\Lastivka\lastivka_core\scripts\stop_lastivka.ps1" @args
}

function Restart-Lastivka {
  Stop-Lastivka | Out-Null
  Start-Sleep -Milliseconds 500
  Start-Lastivka
}

Set-Alias gls Get-LastivkaStatus
Set-Alias sls Start-Lastivka
Set-Alias rls Restart-Lastivka
