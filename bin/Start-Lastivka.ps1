# bin/Start-Lastivka.ps1 — безпечний старт ядра Lastivka з gate-перевіркою, PID і логом
param(
  [switch]$Apply,
  [switch]$DryRun,
  [switch]$Quiet
)

# --- Налаштування шляхів ---
$Root        = "C:\Lastivka"
$CoreScript  = "C:\Lastivka\lastivka_core\Start-Lastivka.ps1"
$Flag        = "C:\Lastivka\archive\core_clean_20250909_104829\C_Lastivka\ALLOW_APPLY.flag"
$LogDir      = "C:\Lastivka\lastivka_core\logs"
$PidFile     = "C:\Lastivka\temp\lastivka.pid"
New-Item -ItemType Directory -Force -Path $LogDir, (Split-Path $PidFile) | Out-Null
$LogPath     = Join-Path $LogDir "start_lastivka.log"

function Write-Log($msg){
  if($Quiet){ return }
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$ts $msg" | Out-File -FilePath $LogPath -Append -Encoding utf8
  Write-Host $msg
}

# --- Gate: взаємовиключні ключі + ALLOW_APPLY.flag ---
if ($Apply -and $DryRun) {
  Write-Error "[gate] не можна одночасно --apply і --dry-run"
  exit 2
}

$ModeArg = "--dry-run"
$ExitCode = 0
if ($Apply) {
  if (Test-Path $Flag) {
    $ModeArg = "--apply"
    Write-Log "[gate] ALLOW_APPLY.flag знайдено → режим APPLY"
  } else {
    Write-Warning "[gate] прапорця немає → примусовий DRY-RUN"
    Write-Log     "[gate] прапорця немає → примусовий DRY-RUN"
    $ExitCode = 1   # попередження
  }
} else {
  Write-Log "[gate] ключ --apply не задано → DRY-RUN"
}

# --- Старт ядра у новому процесі PowerShell і запис PID для watchdog ---
Set-Location $Root
if (-not (Test-Path $CoreScript)) {
  Write-Error "[start] не знайдено $CoreScript"
  exit 2
}

Write-Log "[start] запуск ядра: $CoreScript $ModeArg"
$p = Start-Process -FilePath "powershell" `
                   -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$CoreScript`"",$ModeArg) `
                   -PassThru
if ($null -eq $p -or $p.HasExited) {
  Write-Error "[start] не вдалося стартувати ядро"
  exit 2
}

# зберігаємо PID для watchdog
"$($p.Id)" | Out-File -FilePath $PidFile -Encoding ascii -Force
Write-Log "[start] ядро запущено, PID=$($p.Id) → $PidFile"

exit $ExitCode
