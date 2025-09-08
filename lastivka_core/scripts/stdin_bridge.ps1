# --- cleanup ---
if ($proc -and -not $proc.HasExited) { $proc.Kill(); Start-Sleep 1 }
Get-EventSubscriber | Unregister-Event -ErrorAction SilentlyContinue
Remove-Variable fsw,timer,lastSent,lastStamp,lastWrite,proc,inFile -Scope Script -ErrorAction SilentlyContinue

# --- UTF-8 консоль/IO ---
chcp 65001 | Out-Null
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding           = New-Object System.Text.UTF8Encoding($false)

# --- параметри ---
$workDir = "C:\Lastivka\lastivka_core"
$baseDir = "C:\Lastivka"
$null = New-Item -Path "$baseDir\temp" -ItemType Directory -Force
$script:inFile = "$baseDir\temp\say.txt"

# --- запуск Ластівки з відкритим stdin ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "python"
$psi.Arguments = "-u -m main.lastivka --no-tts"
$psi.WorkingDirectory = $workDir
$psi.UseShellExecute = $false
$psi.RedirectStandardInput  = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.CreateNoWindow = $true
$psi.WindowStyle   = 'Hidden'
$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"

$script:proc = [System.Diagnostics.Process]::Start($psi)
$script:proc.StandardInput.AutoFlush = $true
$script:proc.BeginOutputReadLine()
Register-ObjectEvent -InputObject $script:proc -EventName OutputDataReceived -Action { if ($EventArgs.Data) { Write-Host "[APP] $($EventArgs.Data)" } } | Out-Null
$script:proc.BeginErrorReadLine()
Register-ObjectEvent -InputObject $script:proc -EventName ErrorDataReceived -Action { if ($EventArgs.Data) { Write-Host "[ERR] $($EventArgs.Data)" } } | Out-Null

# --- say.txt ---
if (-not (Test-Path $script:inFile)) { New-Item -Path $script:inFile -ItemType File | Out-Null }
Start-Process notepad.exe $script:inFile
Write-Host "`nГотово. Пиши у $script:inFile, натискай Ctrl+S."

# --- опитувач: 1 відправка на 1 збереження ---
$script:lastSent  = $null
$script:lastWrite = [datetime]::MinValue

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
            if ($sr) { $sr.Close() }; $fs.Close()
        }

        $lastLine = ($content -split '\r?\n') | Where-Object { $_.Trim() -ne '' } | Select-Object -Last 1
        if ($lastLine -and $lastLine -ne $script:lastSent) {
            $script:lastSent = $lastLine
            if ($script:proc -and -not $script:proc.HasExited) { $script:proc.StandardInput.WriteLine($lastLine) }
            Write-Host ">> Надіслано: $lastLine"
        }
    } catch { }
    Start-Sleep -Milliseconds 250
}
