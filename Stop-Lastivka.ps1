$ErrorActionPreference = "SilentlyContinue"
$lock = "C:\Lastivka\temp\lastivka.pid"

function Get-DescendantPids([int]$ppid){
  $procs = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId
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

function Kill-Tree([int]$rootPid){
  if (-not $rootPid) { return }
  $kids = Get-DescendantPids -ppid $rootPid
  foreach($k in $kids){ cmd /c "taskkill /PID $k /T /F" | Out-Null }
  cmd /c "taskkill /PID $rootPid /T /F" | Out-Null
}

if (Test-Path $lock) {
  $pid = (Get-Content $lock | Select-Object -First 1) -as [int]
  if ($pid -and $pid -ne $PID) { Kill-Tree -rootPid $pid }
  Remove-Item $lock -Force
} else {
  taskkill /IM python.exe /T /F | Out-Null
  taskkill /IM pythonw.exe /T /F | Out-Null
  taskkill /IM py.exe /T /F | Out-Null
}
"Stopped."
