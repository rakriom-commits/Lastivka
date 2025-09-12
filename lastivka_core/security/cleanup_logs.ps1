$dir = "C:\Lastivka\lastivka_core\logs"
if (Test-Path $dir) {
  Get-ChildItem $dir -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -Force
}
