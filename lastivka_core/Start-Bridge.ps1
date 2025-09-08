# --- Start-Bridge.ps1 ---
# Місток: Notepad -> say.txt -> stdin Lastivka (без TTS)

# 1) Старт чисто
Get-EventSubscriber | Unregister-Event -ErrorAction SilentlyContinue
Remove-Variable fsw,timer,lastSent,lastWrite,proc,inFile -Scope Script -ErrorAction SilentlyContinue

# 2) Параметри і кодування
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding           = New-Object System.Text.UTF8Encoding($false)
$projectRoot = "C:\Lastivka"
$coreDir     = Join-Path $projectRoot "lastivka_core"
$null = New-Item -Path "$projectRoot\temp" -ItemType Directory -Force
$script:inFile = "$projectRoot\temp\say.txt"

# 3) Запуск Lastivka з відкритим stdin (без TTS)
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = "python"
$psi.Arguments = "-u -m lastivka_core.main.lastivka"
$psi.WorkingDirectory = $projectRoot        # щоб пакет lastivka_core був у sys.path
$psi.UseShellExecute = $false
$psi.RedirectStandardInput  = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.CreateNoWindow = $true
$psi.WindowStyle    = 'Hidden'
$psi.EnvironmentVariables["PYTHONPATH"]       = $projectRoot
$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"

$script:proc = [System.Diagnostics.Process]::Start($psi)
if (-not $script:proc) { Write-Host "[ERR] Не вдалося стартувати python"; exit 1 }
$script:proc.StandardInput.AutoFlush = $true
$script:proc.BeginOutputReadLine()
Register-ObjectEvent -InputObject $script:proc -EventName OutputDataReceived -Action { if ($EventArgs.Data) { Write-Host "[APP] $($EventArgs.Data)" } } | Out-Null
$script:proc.BeginErrorReadLine()
Register-ObjectEvent -InputObject $script:proc -EventName ErrorDataReceived  -Action { if ($EventArgs.Data) { Write-Host "[ERR] $($EventArgs.Data)" } } | Out-Null

# 4) Підготувати say.txt і відкрити Блокнот
if (-not (Test-Path $script:inFile)) { New-Item -Path $script:inFile -ItemType File | Out-Null }
Start-Process notepad.exe $script:inFile
Write-Host ""
Write-Host "Готово. Пиши у say.txt (C:\Lastivka\temp\), натискай Ctrl+S. Зупинка — Ctrl+C."
Write-Host ""

# 5) Одна відправка на одне збереження
$script:lastSent  = $null
$script:lastWrite = [datetime]::MinValue

try {
  while ($true) {
    try {
      $fi = Get-Item -LiteralPath $script:inFile -ErrorAction Stop
      $curWrite = $fi.LastWriteTimeUtc
      if ($curWrite -eq $script:lastWrite) { Start-Sleep -Milliseconds 250; continue }
      $script:lastWrite = $curWrite

      $fs = [System.IO.File]::Open($script:inFile,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
      try {
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true)
        $content = $sr.ReadToEnd()
      } finally {
        if ($sr) { $sr.Close() }
        $fs.Close()
      }

      $lastLine = ($content -split '\r?\n') | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1
      if ($lastLine -and $lastLine -ne $script:lastSent) {
        $script:lastSent = $lastLine
        if ($script:proc -and -not $script:proc.HasExited) {
          $script:proc.StandardInput.WriteLine($lastLine)
          Write-Host ">> Надіслано: $lastLine"
        } else {
          Write-Host "[WARN] Процес не активний; рядок НЕ відправлено."
        }
      }
    } catch { }
    Start-Sleep -Milliseconds 250
  }
}
finally {
  Get-EventSubscriber | Unregister-Event -ErrorAction SilentlyContinue
  if ($script:proc -and -not $script:proc.HasExited) { $script:proc.Kill() }
  Remove-Variable fsw,timer,lastSent,lastWrite,proc,inFile -Scope Script -ErrorAction SilentlyContinue
  Write-Host ""
  Write-Host "[bridge] Зупинено і прибрано."
}
# --- EOF ---

