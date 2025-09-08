# ==================== Start-Lastivka.ps1 вЂ” v3.0 ====================
# Р‘РµР·РїРµС‡РЅРёР№ СЃС‚Р°СЂС‚ Lastivka Core + Р»РѕРі-С…Р°СѓСЃРєС–РїС–РЅРі + РЅР°РґС–Р№РЅРёР№ PID-lock
# РћРїС†С–С—:
#   -NoTTS     в†’ РІРёРјРєРЅСѓС‚Рё РѕР·РІСѓС‡РєСѓ (ENV LASTIVKA_NO_TTS=1)
#   -Force     в†’ С–РіРЅРѕСЂСѓРІР°С‚Рё РїСЂРѕС†РµСЃ-СЃРєР°РЅ (Р°Р»Рµ РЅРµ PID-lock, СЏРєС‰Рѕ РїСЂРѕС†РµСЃ Р¶РёРІРёР№)
#   -QuarantineMode <auto|off|strict> в†’ РїРµСЂРµРІРёР·РЅР°С‡РёС‚Рё РїРѕР»С–С‚РёРєСѓ В«Р—Р°РІС–СЃРёВ»

param(
  [switch]$NoTTS,
  [switch]$Force,
  [ValidateSet('auto','off','strict')]
  [string]$QuarantineMode = $null
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- РљРѕРЅСЃРѕР»СЊ UTF-8 ---
try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
} catch {}

# --- РЁР»СЏС…Рё ---
$ProjectRoot = 'C:\Lastivka'
$PkgRoot     = Join-Path $ProjectRoot 'lastivka_core'
$TempDir     = Join-Path $ProjectRoot 'temp'
$LogDir      = Join-Path $PkgRoot 'logs'
$LockFile    = Join-Path $TempDir 'lastivka.pid'
$SayFile     = Join-Path $TempDir 'say.txt'
$SayLink     = Join-Path $ProjectRoot 'say.txt'

foreach ($d in @($TempDir, $LogDir)) {
  if (-not (Test-Path -LiteralPath $d)) {
    New-Item -ItemType Directory -Path $d | Out-Null
  }
}

# --- say.txt + hardlink (РґР»СЏ С€РІРёРґРєРёС… РєРѕРјР°РЅРґ РіРѕР»РѕСЃСѓ) ---
if (-not (Test-Path -LiteralPath $SayFile)) { New-Item -ItemType File -Path $SayFile | Out-Null }
try {
  $needLink = $true
  if (Test-Path -LiteralPath $SayLink) {
    $list = & cmd /c "fsutil hardlink list `"$SayLink`"" 2>$null
    if ($list -and ($list -match [regex]::Escape($SayFile))) { $needLink = $false }
    else { Remove-Item -LiteralPath $SayLink -Force -ErrorAction SilentlyContinue }
  }
  if ($needLink) { & cmd /c "fsutil hardlink create `"$SayLink`" `"$SayFile`"" | Out-Null }
} catch {}

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
  throw ("Project path not found: {0}" -f $ProjectRoot)
}
Set-Location $ProjectRoot

# --- ENV ---
$env:PYGAME_HIDE_SUPPORT_PROMPT = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = "$ProjectRoot;$PkgRoot" + ($(if ($env:PYTHONPATH) { ';' + $env:PYTHONPATH } else { '' }))
if ($NoTTS) { $env:LASTIVKA_NO_TTS = '1' }
# С‚СЂРёРіРµСЂРё (СЏРєС‰Рѕ С‚СЂРµР±Р°) в†’ СЂРѕР·РєРѕРјРµРЅС‚СѓР№:
# $env:LASTIVKA_TRIGGERS_PATH = Join-Path $PkgRoot 'config\core\triggers.json'
# РїРѕР»С–С‚РёРєР° Р—Р°РІС–СЃРё
if ($QuarantineMode) { $env:LASTIVKA_QUARANTINE_MODE = $QuarantineMode }
elseif (-not $env:LASTIVKA_QUARANTINE_MODE) { $env:LASTIVKA_QUARANTINE_MODE = 'auto' }

# --- Р›РµРіРєРёР№ РїСЂРµРї-С…Р°СѓСЃРєС–РїС–РЅРі Сѓ РєРѕСЂРµРЅС– logs ---
$whitelist = @('lastivka.log','guard.log','user_input.log','session_status.json','detected_emotion.json','memory_store.json')

Get-ChildItem $LogDir -Filter '*.log.err' -File -Recurse |
  Where-Object Length -eq 0 |
  Remove-Item -Force -ErrorAction SilentlyContinue

Get-ChildItem $LogDir -File |
  Where-Object { $whitelist -notcontains $_.Name } |
  Remove-Item -Force -ErrorAction SilentlyContinue

# Р РѕС‚Р°С†С–СЏ user_input.log СЏРєС‰Рѕ > 5MB
$ui = Join-Path $LogDir 'user_input.log'
if ((Test-Path $ui) -and ((Get-Item $ui).Length -gt 5MB)) {
  $stamp = Get-Date -Format yyyyMMdd_HHmmss
  $arch  = Join-Path $LogDir 'archive'
  New-Item $arch -ItemType Directory -Force | Out-Null
  Move-Item $ui (Join-Path $arch "user_input_$stamp.log") -Force
  New-Item $ui -ItemType File | Out-Null
}

# --- Single-instance guard: РїСЂРѕС†РµСЃ-СЃРєР°РЅ (РјРѕР¶РЅР° РїСЂРѕРїСѓСЃС‚РёС‚Рё С„Р»Р°РіРѕРј -Force) ---
if (-not $Force) {
  $existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    ($_.'Name' -match '^(py|python|pythonw)(\.exe)?$') -and
    ($_.CommandLine -match '(-m|\s)lastivka_core(\.main)?\.lastivka(\s|$)|lastivka_core\\main\\lastivka\.py')
  }
  if ($existing) {
    $pids = ($existing | Select-Object -ExpandProperty ProcessId) -join ', '
    Write-Host "[SKIP] Lastivka already running (PID(s): $pids)"
    return
  }
}

# --- РќР°РґС–Р№РЅРёР№ PID-lock (РїРµСЂРµРІС–СЂСЏС”РјРѕ СЃС‚Р°СЂРёР№ PID РґРѕС‡С–СЂРЅСЊРѕРіРѕ python, РЅРµ PS) ---
if (Test-Path -LiteralPath $LockFile) {
  try {
    $oldPid = (Get-Content -LiteralPath $LockFile -ErrorAction Stop).Trim()
    if ($oldPid -match '^\d+$') {
      $pOld = Get-Process -Id [int]$oldPid -ErrorAction SilentlyContinue
      if ($pOld) { throw "вљ пёЏ Lastivka РІР¶Рµ Р·Р°РїСѓС‰РµРЅР° (PID=$oldPid). Р—Р°РІРµСЂС€Рё РїРѕРїРµСЂРµРґРЅС–Р№ РїСЂРѕС†РµСЃ РїРµСЂРµРґ СЃС‚Р°СЂС‚РѕРј." }
    }
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
  } catch {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
  }
}

# --- Р›РѕРіРё Р·Р°РїСѓСЃРєСѓ/СЂРµРґС–СЂРµРєС‚ ---
$ts     = Get-Date -Format yyyyMMdd_HHmmss
$Launch = Join-Path $LogDir ("launch_{0}.txt" -f $ts)
$PyOut  = Join-Path $LogDir ("python_{0}.log" -f $ts)
$PyErr  = Join-Path $LogDir ("python_{0}.log.err" -f $ts)

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Launching Lastivka..." | Out-File -FilePath $Launch -Encoding utf8 -Append
"BASE=$ProjectRoot`r`nCORE=$PkgRoot`r`nPYTHONPATH=$($env:PYTHONPATH)`r`nTRIGGERS=$($env:LASTIVKA_TRIGGERS_PATH)`r`nQUARANTINE=$($env:LASTIVKA_QUARANTINE_MODE)" |
  Out-File -FilePath $Launch -Encoding utf8 -Append

# --- Р РѕР·РІКјСЏР·Р°РЅРЅСЏ Python ---
function Resolve-Python {
  $venvPy = Join-Path $PkgRoot '.venv\Scripts\python.exe'
  if (Test-Path -LiteralPath $venvPy) { return @{File="`"$venvPy`""; Args=@()} }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return @{File='py'; Args=@('-3')} }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return @{File='python'; Args=@()} }

  throw 'Python not found. Install Python 3.10+ or create .venv in lastivka_core.'
}

$pySpec  = Resolve-Python
$PyFile  = $pySpec.File
$PyArgs  = @($pySpec.Args + @('-X','utf8','-u','-m','lastivka_core.main.lastivka','--no-single-instance','--force-unlock'))

# --- Р—Р°РїСѓСЃРє РґРѕС‡С–СЂРЅСЊРѕРіРѕ РїСЂРѕС†РµСЃСѓ Р· СЂРµРґС–СЂРµРєС‚РѕРј (СЂРѕР±РѕС‡Р° С‚РµРєР° = $PkgRoot) ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName               = $PyFile
$psi.Arguments              = ($PyArgs -join ' ')
$psi.WorkingDirectory       = $PkgRoot
$psi.UseShellExecute        = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true

$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
$p.Start() | Out-Null

# РџРёС€РµРјРѕ Сѓ LockFile PID РґРѕС‡С–СЂРЅСЊРѕРіРѕ Python (СЃР°РјРµ Р№РѕРіРѕ, РЅРµ PowerShell)
$p.Id | Out-File -FilePath $LockFile -Encoding ascii -Force

# Р—Р»РёРІР°С”РјРѕ РІРёРІС–Рґ Сѓ С„Р°Р№Р»Рё
$p.StandardOutput.ReadToEnd() | Out-File -FilePath $PyOut -Encoding utf8
$p.StandardError.ReadToEnd()  | Out-File -FilePath $PyErr -Encoding utf8
$p.WaitForExit()

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ExitCode=$($p.ExitCode)" | Out-File -FilePath $Launch -Encoding utf8 -Append

# --- РџРѕСЃС‚-С…Р°СѓСЃРєС–РїС–РЅРі: СЃРєР»Р°РґР°С”РјРѕ РґСЂС–Р±РЅС– Р»РѕРіРё Сѓ runs\YYYYMMDD, С‡РёСЃС‚РёРјРѕ СЃС‚Р°СЂРµ ---
$day   = Get-Date -Format yyyyMMdd
$runs  = Join-Path $LogDir "runs\$day"
New-Item $runs -ItemType Directory -Force | Out-Null

$patterns = @('python_*.log','python_*.log.err','launch_*.txt','run_*.txt')
foreach ($pat in $patterns) {
  Get-ChildItem $LogDir -Filter $pat -File -ErrorAction SilentlyContinue |
    Move-Item -Destination $runs -Force
}

# С‡РёСЃС‚РёРјРѕ runs СЃС‚Р°СЂС€Рµ 14 РґРЅС–РІ
Get-ChildItem (Join-Path $LogDir 'runs') -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# РїСЂРёР±РёСЂР°С”РјРѕ quarantine_* (Сѓ С‚РµР±Рµ С” СЂСѓС‡РЅС– Р±РµРєР°РїРё)
Get-ChildItem "$LogDir\quarantine_*" -Directory -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# РїСЂРёР±РёСЂР°С”РјРѕ lock, СЏРєС‰Рѕ РІС–РЅ РЅР°С€
try {
  $cur = (Get-Content -LiteralPath $LockFile -ErrorAction Stop).Trim()
  if ($cur -eq "$($p.Id)") {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
  }
} catch {}

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Post-run housekeeping done." | Out-File -FilePath $Launch -Encoding utf8 -Append

# РЈ РєРѕРЅСЃРѕР»СЊРЅРѕРјСѓ С…РѕСЃС‚С– Р·Р°С‚СЂРёРјРєР° Р·Р°РєСЂРёС‚С‚СЏ РІС–РєРЅР° (РѕРїС†С–Р№РЅРѕ)
if ($Host.Name -like '*ConsoleHost*') {
  Write-Host ""
  Read-Host 'Press Enter to close window'
}
# ==================== /Start-Lastivka.ps1 ====================
