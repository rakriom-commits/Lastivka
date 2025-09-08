# Start-Bridge_v2_tmp.ps1  (debounce + dedupe + clean shutdown)
param([switch]$NoTTS)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$BASE   = 'C:\Lastivka'
$TEMP   = Join-Path $BASE 'temp'
$SAY    = Join-Path $TEMP 'say.txt'
$LOGDIR = Join-Path $BASE 'lastivka_core\logs'
$PIDF   = Join-Path $TEMP 'lastivka.pid'
$BRIDGE_NAME = 'LastivkaBridge'

New-Item -ItemType Directory -Force -Path $TEMP   | Out-Null
New-Item -ItemType Directory -Force -Path $LOGDIR | Out-Null
if (-not (Test-Path -LiteralPath $SAY)) { New-Item -ItemType File -Force -Path $SAY | Out-Null }

# single-instance
$mutex = New-Object System.Threading.Mutex($false, "Global\$BRIDGE_NAME")
if (-not $mutex.WaitOne(0, $false)) { Write-Host "[bridge] Вже запущено. Вихід."; exit 0 }

try {
  "# $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  START pid=$PID" | Out-File -FilePath (Join-Path $LOGDIR "bridge_$(Get-Date -Format 'yyyyMMdd').log") -Append -Encoding utf8
  "@pid=$PID`n@started=$(Get-Date -Format o)" | Out-File -FilePath $PIDF -Encoding ascii -Force

  $USE_TTS = -not $NoTTS.IsPresent -and -not [bool]$env:NO_TTS -and -not [bool]$env:LASTIVKA_NO_TTS

  $proc=$null; $cmd=$env:LASTIVKA_CMD
  if ($cmd) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName  = 'powershell.exe'
    $psi.Arguments = "-NoLogo -NoProfile -Command $cmd"
    $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true; $psi.RedirectStandardInput=$true
    $proc = New-Object System.Diagnostics.Process; $proc.StartInfo=$psi; $null=$proc.Start()
  }

  $script:lastChange = Get-Date
  $script:pending = $false
  $script:busy = $false
  $script:lastLine = $null
  $script:lastLineSentAt = Get-Date 0

  function Send-LastLine {
    try {
      $script:busy = $true
      if (-not (Test-Path -LiteralPath $SAY)) { return }
      $tail = Get-Content -LiteralPath $SAY -Tail 50 -Encoding UTF8
      if (-not $tail) { return }
      $line = ($tail | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Last 1)
      if (-not $line) { return }
      $now = Get-Date
      if ($line -eq $script:lastLine -and ($now - $script:lastLineSentAt).TotalSeconds -lt 1) { return }
      if ($proc -and -not $proc.HasExited) { $proc.StandardInput.WriteLine($line); $proc.StandardInput.Flush() }
      $script:lastLine = $line; $script:lastLineSentAt = $now
    } finally { $script:busy = $false }
  }

  $fsw = New-Object System.IO.FileSystemWatcher
  $fsw.Path  = [System.IO.Path]::GetDirectoryName($SAY)
  $fsw.Filter= [System.IO.Path]::GetFileName($SAY)
  $fsw.IncludeSubdirectories = $false
  $fsw.NotifyFilter = [IO.NotifyFilters]'FileName, LastWrite, Size'

  $onFsEvent = { $script:lastChange = Get-Date; $script:pending = $true }

  $subs=@()
  $subs += Register-ObjectEvent -InputObject $fsw -EventName Changed -SourceIdentifier "$BRIDGE_NAME.Changed" -Action $onFsEvent
  $subs += Register-ObjectEvent -InputObject $fsw -EventName Created -SourceIdentifier "$BRIDGE_NAME.Created" -Action $onFsEvent
  $subs += Register-ObjectEvent -InputObject $fsw -EventName Renamed -SourceIdentifier "$BRIDGE_NAME.Renamed" -Action $onFsEvent
  $fsw.EnableRaisingEvents = $true

  $timer = New-Object System.Timers.Timer
  $timer.Interval = 150
  $timer.AutoReset = $true
  $subs += Register-ObjectEvent -InputObject $timer -EventName Elapsed -SourceIdentifier "$BRIDGE_NAME.Timer" -Action {
    if (-not $script:pending) { return }
    $gap = (Get-Date) - $script:lastChange
    if ($gap.TotalMilliseconds -ge 120 -and -not $script:busy) { $script:pending = $false; Send-LastLine }
  }
  $timer.Start()

  Write-Host "[bridge] Запущено TMP. Спостерігаю за $SAY (debounce=120ms, dedupe=1s). Ctrl+C для виходу."

  $global:__bridge_running = $true
  $cleanup = {
    try {
      if ($timer) { $timer.Stop() }
      if ($subs)  { $subs | ForEach-Object { Unregister-Event -SourceIdentifier $_.SourceIdentifier -ErrorAction SilentlyContinue } }
      if ($fsw)   { $fsw.EnableRaisingEvents = $false; $fsw.Dispose() }
      Get-Event   | Remove-Event -ErrorAction SilentlyContinue
      if (Test-Path -LiteralPath $PIDF) { Remove-Item -LiteralPath $PIDF -Force -ErrorAction SilentlyContinue }
      if ($proc -and -not $proc.HasExited) { $proc.Close() | Out-Null }
      Write-Host "[bridge] Зупинено і прибрано."
    } catch {}
  }

  Register-EngineEvent -SourceIdentifier Console_CancelKeyPress -Action { $global:__bridge_running = $false } | Out-Null

  while ($global:__bridge_running) { Start-Sleep -Milliseconds 200 }
}
finally { & $cleanup; if ($mutex){ $mutex.ReleaseMutex() | Out-Null; $mutex.Dispose() } }
