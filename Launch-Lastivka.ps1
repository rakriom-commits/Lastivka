# Minimal, ASCII-only launcher for Lastivka.
# Headless by default; console input ? use "py" (not pyw) to have stdin.
$ErrorActionPreference = "Stop"

$Root = "C:\Lastivka"
$Temp = Join-Path $Root "temp"
$Logs = Join-Path $Root "lastivka_core\logs"
$Lock = Join-Path $Temp "lastivka.pid"
foreach($d in @($Temp,$Logs)){ if(-not (Test-Path $d)){ New-Item -ItemType Directory -Path $d | Out-Null } }

$ts    = (Get-Date -Format "yyyyMMdd_HHmmss")
$RunLog= Join-Path $Logs ("launch_"  + $ts + ".txt")
$PyOut = Join-Path $Logs ("python_"  + $ts + ".log")
$PyErr = Join-Path $Logs ("python_"  + $ts + ".log.err")

function Write-Log([string]$msg){
  $line = ("[{0}] {1}" -f ((Get-Date).ToString("o")),$msg)
  Write-Host $line
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::AppendAllText($RunLog, $line + "`r`n", $utf8NoBom)
}

function Test-ProcAlive([int]$pidNum){
  try { Get-Process -Id $pidNum -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

function Get-DescendantPids([int]$ppid){
  $procs = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine
  $q = New-Object System.Collections.Generic.Queue[System.Int32]
  $seen = New-Object System.Collections.Generic.HashSet[System.Int32]
  $out = New-Object System.Collections.Generic.List[System.Int32]
  $q.Enqueue($ppid)
  while($q.Count -gt 0){
    $cur = $q.Dequeue()
    if ($seen.Contains($cur)) { continue } else { $seen.Add($cur) | Out-Null }
    foreach($p in $procs | Where-Object { $_.ParentProcessId -eq $cur }){
      $out.Add([int]$p.ProcessId) | Out-Null
      $q.Enqueue([int]$p.ProcessId)
    }
  }
  return ,$out.ToArray()
}

function Find-PythonChild([int]$ppid, [int]$timeoutMs=6000, [int]$stepMs=300){
  $deadline = (Get-Date).AddMilliseconds($timeoutMs)
  while((Get-Date) -lt $deadline){
    $kids = Get-DescendantPids -ppid $ppid
    if ($kids.Count -gt 0) {
      $plist = Get-CimInstance Win32_Process | Where-Object { $kids -contains $_.ProcessId }
      $hit = $plist | Where-Object { $_.Name -match '^(pythonw?)(\.exe)?$' -and $_.CommandLine -match 'lastivka_core\.main\.lastivka' } | Select-Object -First 1
      if ($hit) { return [int]$hit.ProcessId }
      $hit = $plist | Where-Object { $_.Name -match '^(pythonw?)(\.exe)?$' } | Select-Object -First 1
      if ($hit) { return [int]$hit.ProcessId }
    }
    Start-Sleep -Milliseconds $stepMs
  }
  return $null
}

# ---- Environment for headless + console input + offline TTS
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:LASTIVKA_NO_GUI = "1"
$env:LASTIVKA_INPUT_MODE = "console"
$env:LASTIVKA_TTS_BACKEND = "offline"
$env:LASTIVKA_VOICE_FAST_DISABLE = "1"

# Ensure PYTHONPATH
$pp = "C:\Lastivka;C:\Lastivka\lastivka_core"
if ($env:PYTHONPATH -and $env:PYTHONPATH -ne "") { $env:PYTHONPATH = $pp + ";" + $env:PYTHONPATH } else { $env:PYTHONPATH = $pp }
Write-Log "Launcher start"
Write-Log ("PYTHONPATH = {0}" -f $env:PYTHONPATH)

# Single-instance by real child PID in lock
if (Test-Path $Lock) {
  $existing = (Get-Content $Lock | Select-Object -First 1) -as [int]
  if ($existing -and (Test-ProcAlive $existing)) { Write-Log ("SKIP: already running (PID={0})" -f $existing); exit 0 }
  Write-Log ("Stale lock (PID={0}) -> removing" -f $existing)
  Remove-Item $Lock -Force -ErrorAction SilentlyContinue
}

# IMPORTANT: console input ? use "py" (not pyw), so stdin exists
$pyExe  = "py"
$pyArgs = "-3 -X utf8 -u -m lastivka_core.main.lastivka"
Write-Log ("Launch: {0} {1}" -f $pyExe, $pyArgs)
Write-Log ("OutLog: {0}" -f $PyOut)
Write-Log ("ErrLog: {0}" -f $PyErr)

$proc = Start-Process -FilePath $pyExe -ArgumentList $pyArgs -PassThru -WorkingDirectory $Root `
         -RedirectStandardOutput $PyOut -RedirectStandardError $PyErr -WindowStyle Hidden
Write-Log ("py PID={0}" -f $proc.Id)

$pyChild = Find-PythonChild -ppid $proc.Id -timeoutMs 6000 -stepMs 300
$realPid = if ($pyChild) { $pyChild } else { $proc.Id }
if ($pyChild) { Write-Log ("Resolved python PID={0} (from py PID={1})" -f $realPid, $proc.Id) }
else { Write-Log ("Using py PID (no python child found) PID={0}" -f $realPid) }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Lock, "$realPid", $utf8NoBom)
Write-Log ("Lock -> {0}" -f $Lock)

Start-Sleep -Milliseconds 300
if (-not (Test-ProcAlive $realPid)) {
  Write-Log "Child exited too fast. ERR tail:"
  if (Test-Path $PyErr) { Get-Content $PyErr -Tail 30 | ForEach-Object { Write-Log $_ } }
}

try {
  Wait-Process -Id $realPid
  Write-Log ("Child exited PID={0}" -f $realPid)
} finally {
  if (Test-Path $Lock) {
    $cur = (Get-Content $Lock | Select-Object -First 1) -as [int]
    if ($cur -eq $realPid) { Remove-Item $Lock -Force -ErrorAction SilentlyContinue; Write-Log "Lock removed" }
    else { Write-Log ("Lock not removed (cur={0} child={1})" -f $cur,$realPid) }
  }
}
Write-Log "Launcher end"
