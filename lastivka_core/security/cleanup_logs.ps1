# cleanup_logs.ps1 → чистка і архівування логів Ластівки
$dir = "C:\Lastivka\lastivka_core\logs"
$archive = "C:\Lastivka\lastivka_core\logs\archive"
$report = Join-Path $dir "cleanup_report.txt"

New-Item -ItemType Directory -Force -Path $archive | Out-Null

if (Test-Path $dir) {
    $old = Get-ChildItem $dir -File | Where-Object {
        $_.Length -eq 0 -or $_.LastWriteTime -lt (Get-Date).AddDays(-14)
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    if ($old.Count -gt 0) {
        foreach ($f in $old) {
            $dest = Join-Path $archive $f.Name
            Move-Item $f.FullName $dest -Force
        }
        $names = $old | Select-Object -ExpandProperty Name
        $msg = "[$timestamp] 🧹 Перенесено $($old.Count) файлів у archive: $($names -join ', ')"
    } else {
        $msg = "[$timestamp] ✅ Немає старих або пустих логів для переносу."
    }

    Write-Host $msg
    Add-Content -Path $report -Value $msg
}
