param(
  [string]$Root    = "C:\Lastivka\gateway\cloud_mailbox",
  [int]   $PollSec = 5
)

# === LOG PATHS ===
$watcherLog = Join-Path $Root 'logs\watcher.log'   # службовий лог watcher-а
$gatewayLog = Join-Path $Root 'logs\gateway.log'   # лог, який може крутити logs.rotate

# Folders & flags
$inbox      = Join-Path $Root 'inbox'
$outbox     = Join-Path $Root 'outbox'
$archive    = Join-Path $Root 'archive'
$quarantine = Join-Path $Root 'quarantine'
$allowFlag  = "C:\Lastivka\ALLOW_APPLY.flag"
$stopFlag   = Join-Path $Root 'STOP.flag'

# Whitelist
$WhitelistFocus = @('verify.integrity','logs.rotate','memory.optimization','report.daily')

# Ensure structure
New-Item $inbox,$outbox,$archive,$quarantine,(Split-Path $watcherLog) -ItemType Directory -Force | Out-Null
New-Item (Split-Path $gatewayLog) -ItemType Directory -Force | Out-Null

# Hydrate OneDrive paths ( harmless if not OneDrive )
try {
  cmd /c attrib +P -U "$Root"                        2>nul | Out-Null
  cmd /c attrib +P -U "$inbox"                       2>nul | Out-Null
  cmd /c attrib +P -U "$outbox"                      2>nul | Out-Null
  cmd /c attrib +P -U (Split-Path $watcherLog)       2>nul | Out-Null
  cmd /c attrib +P -U (Split-Path $gatewayLog)       2>nul | Out-Null
} catch {}

function Write-LineSafe {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Line,
    [int]$Retries = 8,
    [int]$DelayMs = 120
  )
  for($i=0; $i -lt $Retries; $i++){
    try{
      New-Item -ItemType Directory -Force -Path (Split-Path $Path) | Out-Null
      $fs = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::Append,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::ReadWrite
      )
      try{
        $enc = [System.Text.UTF8Encoding]::new($false)
        $sw  = New-Object System.IO.StreamWriter($fs, $enc)
        $sw.WriteLine($Line)
        $sw.Flush()
        $sw.Dispose()
      } finally {
        $fs.Dispose()
      }
      break
    } catch {
      if($i -ge $Retries-1){ throw }
      Start-Sleep -Milliseconds $DelayMs
    }
  }
}

function W-Log([string]$msg){
  try{
    $ts = (Get-Date).ToString('s')
    Write-LineSafe -Path $watcherLog -Line ("{0} {1}" -f $ts, $msg)
  } catch { }
}

function Get-PayloadHash([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$p){
  if (-not $p -or $p -eq "") { return $null }
  if (-not (Test-Path $p))   { return $null }
  try {
    $o = (Get-Content $p -Raw -Encoding UTF8) | ConvertFrom-Json -ErrorAction Stop
    if ($o.PSObject.Properties['sha256']) { $o.PSObject.Properties.Remove('sha256') | Out-Null }
    $payload = $o | ConvertTo-Json -Depth 20 -Compress
    $b = [Text.Encoding]::UTF8.GetBytes($payload)
    $s = [Security.Cryptography.SHA256]::Create()
    return ([BitConverter]::ToString($s.ComputeHash($b))).Replace('-','').ToLowerInvariant()
  } catch { return $null }
}

function Format-Bytes([long]$bytes){
  if($bytes -lt 1KB){ return "$bytes B" }
  $units = "KB","MB","GB","TB"
  $v = [double]$bytes
  foreach($u in $units){
    $v = $v/1KB
    if($v -lt 1024){ return ("{0:N1} {1}" -f $v, $u) }
  }
  return ("{0:N1} PB" -f ($v/1024))
}

function Get-NextTaskPath([string]$Inbox){
  try{
    $files = [System.IO.Directory]::GetFiles($Inbox, '*.task.json')
    if(-not $files -or $files.Count -eq 0){ return $null }
    # найстаріший перший
    return ($files | Sort-Object { (Get-Item $_).LastWriteTime })[0]
  } catch { return $null }
}

W-Log "watcher start (poll=$PollSec s)"
$lastBeat = (Get-Date).AddYears(-1)

while($true){
  if(Test-Path $stopFlag){
    W-Log "STOP.flag present -> idle"
    Start-Sleep -Seconds ([math]::Max(10, $PollSec*2))
    continue
  }

  # Beat раз на ~20с (видно, що живий)
  if ( (New-TimeSpan -Start $lastBeat -End (Get-Date)).TotalSeconds -ge 20 ){
    try{
      $cnt = ([System.IO.Directory]::GetFiles($inbox,'*.task.json')).Count
    } catch { $cnt = -1 }
    W-Log ("beat: inbox_count={0}" -f $cnt)
    $lastBeat = Get-Date
  }

  $taskPath = Get-NextTaskPath $inbox
  if(-not $taskPath){ Start-Sleep -Seconds $PollSec; continue }
  $taskFile = Get-Item $taskPath

  # Read task
  try { $task = Get-Content $taskFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop }
  catch {
    W-Log "bad json: $($taskFile.Name) -> quarantine"
    Move-Item $taskFile.FullName (Join-Path $quarantine $taskFile.Name) -Force
    Start-Sleep -Seconds 1
    continue
  }

  # Basic checks
  if($task.sender -ne 'sofia'){
    W-Log "sender not allowed: $($task.sender)"
    Move-Item $taskFile.FullName (Join-Path $quarantine $taskFile.Name) -Force
    continue
  }
  if(($task.focus -as [string]) -notin $WhitelistFocus){
    W-Log "focus not allowed: $($task.focus)"
    Move-Item $taskFile.FullName (Join-Path $quarantine $taskFile.Name) -Force
    continue
  }

  # --- SAFE payload hash & ACK ---
  $payloadHash = Get-PayloadHash $taskFile.FullName
  if(-not $payloadHash){
    W-Log "hash calc failed -> quarantine: $($task.id)"
    Move-Item $taskFile.FullName (Join-Path $quarantine $taskFile.Name) -Force
    continue
  }
  $hashOk = ($task.sha256 -as [string]) -and ($payloadHash -as [string]) -and ($task.sha256.ToLower() -eq $payloadHash.ToLower())

  # ACK
  $ackObj = @{
    id=$task.id; ts=(Get-Date).ToString("s"); receiver="lastivka"; status="received"; version="gateway-1.0"; hash_ok=$hashOk
  }
  $ackObj | ConvertTo-Json -Depth 6 | Out-File (Join-Path $outbox "$($task.id).ack.json") -Encoding UTF8
  if(-not $hashOk){
    W-Log "hash mismatch -> quarantine: $($task.id)"
    Move-Item $taskFile.FullName (Join-Path $quarantine $taskFile.Name) -Force
    continue
  }

  # Mode
  $dryRun = -not (Test-Path $allowFlag) -or ($task.limits.mode -ne 'safe')
  W-Log "task $($task.id) kind=$($task.kind) focus=$($task.focus) dryRun=$dryRun"

  # ---------------- HANDLERS ----------------
  $artifacts = @()
  $resultSummary = "watcher run (dryRun={0})" -f $dryRun
  $ok = $true

  if ($task.focus -eq 'verify.integrity') {
    $checks = @(
      'C:\Lastivka\memory',
      'C:\Lastivka\memory\snapshots',
      'C:\Lastivka\logs',
      'C:\Lastivka\indices'
    )
    $report = Join-Path $outbox ("verify_integrity_{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))
    $lines = @()
    foreach($p in $checks){
      $exists = Test-Path $p
      $lines += ("[{0}] {1}" -f ($(if($exists){'OK'}else{'MISS'}), $p))
      if(-not $exists){ $ok = $false }
    }
    $lines += ("allow_apply_flag: " + (Test-Path $allowFlag))
    $lines -join "`r`n" | Out-File $report -Encoding UTF8
    $artifacts += $report
    $resultSummary = ("verify.integrity: {0} paths checked; ok={1}" -f $checks.Count, $ok)
  }
  elseif ($task.focus -eq 'logs.rotate') {
    $thresholdBytes = 1MB
    $log = $gatewayLog    # <- єдина прив’язка
    $ok = $true

    if (Test-Path $log) { $size = (Get-Item $log).Length } else { $size = 0 }
    $needRotate = $size -ge $thresholdBytes

    $writes = ($task.limits.writes -as [string])
    $writesAllowed = $writes -and ($writes -in @('guarded','all'))

    if ($needRotate -and -not $dryRun -and $writesAllowed) {
      $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
      $rotated = Join-Path (Split-Path $log) ("gateway_{0}.log" -f $stamp)
      Move-Item $log $rotated -Force
      New-Item -ItemType File -Path $log -Force | Out-Null
      $artifacts += $rotated
      $resultSummary = ('logs.rotate: rotated at ~{0:N0} bytes -> {1}' -f $size, $rotated)
    }
    elseif ($needRotate -and -not $writesAllowed) {
      $resultSummary = ('logs.rotate: blocked (writes={0}) @ ~{1:N0} bytes' -f $writes, $size)
    }
    elseif ($needRotate -and $dryRun) {
      $resultSummary = ('logs.rotate: would rotate @ ~{0:N0} bytes (dryRun)' -f $size)
    }
    else {
      $resultSummary = ('logs.rotate: no action (size={0:N0} bytes)' -f $size)
    }
  }
  elseif ($task.focus -eq 'report.daily') {
    $report = Join-Path $outbox ("report_daily_{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))

    # health
    try { $cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction Stop).CounterSamples[0].CookedValue } catch { $cpu = $null }
    try { $os  = Get-CimInstance Win32_OperatingSystem } catch { $os = $null }
    $ramUsed  = if($os){ ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)*1KB } else { 0 }
    $ramTotal = if($os){ $os.TotalVisibleMemorySize*1KB } else { 0 }
    try {
      $d = Get-PSDrive -Name C -ErrorAction Stop
      $freeDisk = $d.Free
      $totDisk  = $d.Used + $d.Free
    } catch { $freeDisk = 0; $totDisk = 0 }

    # logs
    $gSize = if(Test-Path $gatewayLog){ (Get-Item $gatewayLog).Length } else { 0 }

    # safe values для PS 5.1
    $cpuSafe = if($cpu -ne $null){ [double]$cpu } else { 0 }

    $lines = @()
    $lines += "ts: " + (Get-Date).ToString('s')
    $lines += ("cpu: {0:N1}%" -f $cpuSafe)
    $lines += "ram.used/total: {0} / {1}" -f (Format-Bytes $ramUsed), (Format-Bytes $ramTotal)
    if($totDisk -gt 0){ $lines += "disk(C:).free/total: {0} / {1}" -f (Format-Bytes $freeDisk), (Format-Bytes $totDisk) }
    $lines += "gateway.log: {0}" -f (Format-Bytes $gSize)
    $lines -join "`r`n" | Out-File $report -Encoding UTF8

    $artifacts += $report
    $resultSummary = "report.daily: ok (cpu≈{0:N0}% ram={1}/{2})" -f $cpuSafe, (Format-Bytes $ramUsed), (Format-Bytes $ramTotal)
  }
  elseif ($task.focus -eq 'memory.optimization') {
    # план дій без записів
    $plan = Join-Path $outbox ("memory_opt_plan_{0:yyyyMMdd_HHmmss}.txt" -f (Get-Date))
    $lines = @(
      "ts: " + (Get-Date).ToString('s'),
      ("mode: plan-only (dryrun={0})" -f $dryRun),
      "steps:",
      "  1) scan memory root -> find duplicates (top=$($task.params.top))",
      "  2) propose dedupe ops -> write .plan.json for review",
      "  3) snapshot memory -> snapshots\mem_{timestamp}.json",
      "  4) apply guarded writes only with allow flag"
    )
    $lines -join "`r`n" | Out-File $plan -Encoding UTF8
    $artifacts += $plan
    $resultSummary = "memory.optimization: plan generated (top={0})" -f ($task.params.top)
  }
  else {
    Start-Sleep -Seconds ([math]::Min(($task.limits.max_runtime_s -as [int]), 5))
  }
  # -------------- END HANDLERS --------------

  # --- FINALIZE & WRITE STATUS (always) ---
  if (-not $resultSummary) { $resultSummary = "no summary" }
  if (-not $artifacts)     { $artifacts     = @() }
  if ($ok -isnot [bool])   { $ok = $true }
  $statusObj = [ordered]@{
    id        = $task.id
    ts        = (Get-Date).ToString("s")
    ok        = ($ok -as [bool])
    summary   = $resultSummary
    artifacts = $artifacts
  }
  $stPath = Join-Path $outbox ("{0}.status.json" -f $task.id)
  $statusObj | ConvertTo-Json -Depth 20 | Out-File $stPath -Encoding UTF8

  # ARCHIVE
  $day = (Get-Date).ToString("yyyyMMdd")
  $archDir = Join-Path $archive $day
  New-Item $archDir -ItemType Directory -Force | Out-Null
  Move-Item $taskFile.FullName (Join-Path $archDir $taskFile.Name) -Force
}
