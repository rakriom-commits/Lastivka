param(
  [int]$LookbackHours = 48,          # перевіряємо останні N годин (дефолт 48)
  [string]$OutRoot = "C:\Lastivka\lastivka_core\logs"  # куди писати звіти
)

$ErrorActionPreference = "SilentlyContinue"

function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }
function NowStr(){ return (Get-Date -Format 'yyyyMMdd_HHmmss') }

$TS = NowStr
$OutDir = Join-Path $OutRoot ("software_audit_{0}" -f $TS)
Ensure-Dir $OutDir

$since = (Get-Date).AddHours(-$LookbackHours)

# Helper: Normalize path and test signing
function Normalize-Path([string]$p){
  if([string]::IsNullOrWhiteSpace($p)){ return "" }
  $p = $p.Trim('"')
  # if it's like "C:\Path\app.exe" /something, take the exe path
  if($p -match '^[A-Za-z]:\\'){
    if($p -match '^(?<exe>[A-Za-z]:\\[^"]+?\.exe)\b'){
      return $Matches['exe']
    }
  }
  return $p
}

function Sign-Status([string]$path){
  try{
    if([string]::IsNullOrWhiteSpace($path) -or -not (Test-Path $path)){ return "unknown" }
    $sig = Get-AuthenticodeSignature -LiteralPath $path
    if($sig.Status -eq 'Valid'){ return "signed" }
    if($sig.Status -eq 'NotSigned'){ return "unsigned" }
    return "$($sig.Status)"
  }catch{ return "unknown" }
}

function In-UserArea([string]$path){
  if([string]::IsNullOrWhiteSpace($path)){ return $false }
  $p = $path.ToLower()
  $user = $env:USERNAME.ToLower()
  return ($p -like "*\users\$user\*" -or $p -like "*\appdata\*" -or $p -like "*\temp\*" -or $p -like "*\downloads\*")
}

function Is-ListenerExe([string]$path){
  try{
    $p = Get-Process | Where-Object { $_.Path -and $_.Path -ieq $path }
    if($p){
      $pid = $p.Id
      $listen = Get-NetTCPConnection -State Listen -OwningProcess $pid -ErrorAction SilentlyContinue
      return ($listen -ne $null -and $listen.Count -gt 0)
    }
  } catch {}
  return $false
}

# Collect: Installed programs via registry
$uninstRoots = @(
 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
) | Where-Object { Test-Path $_ }

$apps = @()
foreach($root in $uninstRoots){
  Get-ChildItem $root | ForEach-Object {
    try{
      $dn = (Get-ItemProperty $_.PsPath -ErrorAction Stop)
      $name = $dn.DisplayName
      if([string]::IsNullOrWhiteSpace($name)){ return }
      $loc  = $dn.InstallLocation
      $inst = $null
      if($dn.InstallDate){
        # YYYYMMDD
        $s = "$($dn.InstallDate)"
        if($s -match '^\d{8}$'){ $inst = [datetime]::ParseExact($s, 'yyyyMMdd', $null) }
      }
      $uninst = $dn.UninstallString
      $exe = Normalize-Path $uninst
      if([string]::IsNullOrWhiteSpace($exe) -and $loc){
        # try to guess main exe by newest file in folder
        if(Test-Path $loc){
          $cand = Get-ChildItem $loc -Recurse -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer -and $_.Extension -match '\.exe$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
          if($cand){ $exe = $cand.FullName }
        }
      }
      $apps += [PSCustomObject]@{
        Name = $name
        Version = $dn.DisplayVersion
        Publisher = $dn.Publisher
        InstallDate = $inst
        InstallLocation = $loc
        UninstallExe = $exe
        Source = "Registry"
      }
    } catch {}
  }
}

# Collect: MSI install events
$msiEvents = @()
try{
  $msiEvents = Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='MsiInstaller'; StartTime=$since} |
     Select-Object TimeCreated, Id, Message
} catch {}

# Collect: Service installations (Event ID 7045)
$svcInstallEvents = @()
try{
  $svcInstallEvents = Get-WinEvent -FilterHashtable @{LogName='System'; Id=7045; StartTime=$since} |
    Select-Object TimeCreated, Id, Message
} catch {}

# Collect: Services list with paths and autostart
$services = @()
try{
  $services = Get-CimInstance Win32_Service | Select-Object Name, DisplayName, StartMode, State, PathName
} catch {}

# Collect: Scheduled tasks (file timestamps)
$taskFiles = @()
try{
  $taskDir = 'C:\Windows\System32\Tasks'
  if(Test-Path $taskDir){
    $taskFiles = Get-ChildItem $taskDir -Recurse -File | Where-Object { $_.LastWriteTime -ge $since } |
      Select-Object FullName, LastWriteTime
  }
} catch {}

# Collect: Autoruns (Run/RunOnce)
$autoruns = @()
$runRoots = @(
 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
) | Where-Object { Test-Path $_ }

foreach($r in $runRoots){
  try{
    $kv = Get-ItemProperty $r
    $kv.PSObject.Properties | Where-Object { $_.Name -notin @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider') } |
      ForEach-Object {
        $exe = Normalize-Path ([string]$_.Value)
        $autoruns += [PSCustomObject]@{
          Root = $r
          Name = $_.Name
          Command = $_.Value
          ExePath = $exe
        }
      }
  } catch {}
}

# Build unified findings with risk scoring
$findings = @()

# Registry apps within window (by InstallDate or folder timestamp)
foreach($a in $apps){
  # Determine a plausible install time
  $t = $null
  if($a.InstallDate){ $t = $a.InstallDate }
  elseif($a.InstallLocation -and (Test-Path $a.InstallLocation)){ $t = (Get-Item $a.InstallLocation).LastWriteTime }
  elseif($a.UninstallExe -and (Test-Path $a.UninstallExe)){ $t = (Get-Item $a.UninstallExe).LastWriteTime }

  $within = $false
  if($t){ $within = ($t -ge $since) }

  if($within){
    $exe = $a.UninstallExe
    $signed = Sign-Status $exe
    $listener = Is-ListenerExe $exe
    $auto = $false

    # Cross-link with services
    $svc = $services | Where-Object { $_.PathName -and $exe -and $_.PathName.ToLower().Contains($exe.ToLower()) }
    if($svc -and $svc.StartMode -eq 'Auto'){ $auto = $true }

    # Cross-link with autoruns
    $autoRunHit = $autoruns | Where-Object { $_.ExePath -and $exe -and $_.ExePath.ToLower() -eq $exe.ToLower() }
    if($autoRunHit){ $auto = $true }

    # Risk score
    $score = 0
    $evidence = @()

    $score += 2; $evidence += "fresh_install"
    if($auto){ $score += 2; $evidence += "autostart" }
    if($listener){ $score += 1; $evidence += "network_listener" }
    if($signed -ne "signed"){ $score += 2; $evidence += "not_signed_or_unknown" }
    if([string]::IsNullOrWhiteSpace($a.Publisher)){ $score += 1; $evidence += "no_publisher" }
    if(In-UserArea $exe){ $score += 2; $evidence += "user_area_path" }

    $level = if($score -ge 6){"HIGH"} elseif($score -ge 3){"MEDIUM"} else {"LOW"}

    $findings += [PSCustomObject]@{
      Kind = "Program"
      Name = $a.Name
      Publisher = $a.Publisher
      Version = $a.Version
      Path = $exe
      InstallTime = $t
      AutoStart = $auto
      Signed = $signed
      NetworkListener = $listener
      RiskScore = $score
      RiskLevel = $level
      Evidence = ($evidence -join ';')
    }
  }
}

# Services installed events
foreach($e in $svcInstallEvents){
  $msg = $e.Message
  # Try to parse: "Service Name: X" and "Binary Path: C:\..."
  $svcName = $null; $bin = $null
  if($msg -match "Service Name:\s*(.+?)\r?\n"){ $svcName = $Matches[1].Trim() }
  if($msg -match "Binary Path:\s*(.+?)\r?\n"){ $bin = Normalize-Path $Matches[1].Trim() }
  $signed = Sign-Status $bin
  $listener = Is-ListenerExe $bin
  $auto = $false
  $svc = $services | Where-Object { $_.Name -eq $svcName }
  if($svc -and $svc.StartMode -eq 'Auto'){ $auto = $true }

  $score = 2 # recent service install
  $evidence = @("service_install")
  if($auto){ $score += 2; $evidence += "autostart" }
  if($listener){ $score += 1; $evidence += "network_listener" }
  if($signed -ne "signed"){ $score += 2; $evidence += "not_signed_or_unknown" }
  if(In-UserArea $bin){ $score += 2; $evidence += "user_area_path" }

  $level = if($score -ge 6){"HIGH"} elseif($score -ge 3){"MEDIUM"} else {"LOW"}

  $findings += [PSCustomObject]@{
    Kind = "ServiceInstallEvent"
    Name = $svcName
    Publisher = ""
    Version = ""
    Path = $bin
    InstallTime = $e.TimeCreated
    AutoStart = $auto
    Signed = $signed
    NetworkListener = $listener
    RiskScore = $score
    RiskLevel = $level
    Evidence = ($evidence -join ';')
  }
}

# Scheduled Tasks
foreach($tf in $taskFiles){
  $taskName = $tf.FullName.Substring("C:\Windows\System32\Tasks".Length).TrimStart('\')
  $actPath = ""
  try{
    $t = Get-ScheduledTask -TaskPath ("\{0}\" -f (Split-Path $taskName -Parent)) -TaskName (Split-Path $taskName -Leaf) -ErrorAction SilentlyContinue
    if($t){
      foreach($a in $t.Actions){
        if($a.Execute){ $actPath = Normalize-Path $a.Execute }
      }
    }
  } catch {}
  $signed = Sign-Status $actPath
  $listener = Is-ListenerExe $actPath
  $auto = $true # by nature of scheduled task

  $score = 2 # recent task change
  $evidence = @("scheduled_task")
  if($auto){ $score += 2; $evidence += "autostart" }
  if($listener){ $score += 1; $evidence += "network_listener" }
  if($signed -ne "signed"){ $score += 2; $evidence += "not_signed_or_unknown" }
  if(In-UserArea $actPath){ $score += 2; $evidence += "user_area_path" }

  $level = if($score -ge 6){"HIGH"} elseif($score -ge 3){"MEDIUM"} else {"LOW"}

  $findings += [PSCustomObject]@{
    Kind = "ScheduledTask"
    Name = $taskName
    Publisher = ""
    Version = ""
    Path = $actPath
    InstallTime = $tf.LastWriteTime
    AutoStart = $auto
    Signed = $signed
    NetworkListener = $listener
    RiskScore = $score
    RiskLevel = $level
    Evidence = ($evidence -join ';')
  }
}

# Autoruns that appeared recently (check exe mtime)
foreach($ar in $autoruns){
  $p = $ar.ExePath
  $t = $null
  if($p -and (Test-Path $p)){ $t = (Get-Item $p).LastWriteTime }
  if($t -and $t -ge $since){
    $signed = Sign-Status $p
    $listener = Is-ListenerExe $p
    $score = 2 # recent binary write
    $evidence = @("autorun_recent_binary")
    $score += 2; $evidence += "autostart"
    if($listener){ $score += 1; $evidence += "network_listener" }
    if($signed -ne "signed"){ $score += 2; $evidence += "not_signed_or_unknown" }
    if(In-UserArea $p){ $score += 2; $evidence += "user_area_path" }
    $level = if($score -ge 6){"HIGH"} elseif($score -ge 3){"MEDIUM"} else {"LOW"}

    $findings += [PSCustomObject]@{
      Kind = "Autorun"
      Name = $ar.Name
      Publisher = ""
      Version = ""
      Path = $p
      InstallTime = $t
      AutoStart = $true
      Signed = $signed
      NetworkListener = $listener
      RiskScore = $score
      RiskLevel = $level
      Evidence = ($evidence -join ';')
    }
  }
}

# MSI events summary
$msiOut = Join-Path $OutDir "msi_events.txt"
if($msiEvents -and $msiEvents.Count -gt 0){
  $msiEvents | Sort-Object TimeCreated | Format-Table -AutoSize | Out-String | Out-File -Encoding utf8 $msiOut
}

# Write full findings
$csv = Join-Path $OutDir "software_findings.csv"
$findings | Sort-Object RiskScore -Descending, InstallTime -Descending |
  Export-Csv -NoTypeInformation -Encoding UTF8 $csv

# Focused filter for names like "Autopilot" or "Authenticator"
$focus = $findings | Where-Object { $_.Name -match '(?i)autopilot|authenticat' -or $_.Path -match '(?i)autopilot|authenticat' }
$focusFile = Join-Path $OutDir "focus_autopilot_authenticator.txt"
if($focus){
  $focus | Format-Table -AutoSize | Out-String | Out-File -Encoding utf8 $focusFile
}

# Quick summary
$sum = @()
$sum += "Window: last $LookbackHours hours (since $since)"
$sum += "Findings total: $($findings.Count)"
$sum += "High:   $(@($findings | Where-Object {$_.RiskLevel -eq 'HIGH'}).Count)"
$sum += "Medium: $(@($findings | Where-Object {$_.RiskLevel -eq 'MEDIUM'}).Count)"
$sum += "Low:    $(@($findings | Where-Object {$_.RiskLevel -eq 'LOW'}).Count)"
$sum += ""
$sum += "Files:"
$sum += " - $csv"
if(Test-Path $msiOut){ $sum += " - $msiOut" }
if(Test-Path $focusFile){ $sum += " - $focusFile" }

$sumPath = Join-Path $OutDir "SUMMARY.txt"
$sum -join "`r`n" | Out-File -Encoding utf8 $sumPath

Write-Output ("DONE: " + $sumPath)
