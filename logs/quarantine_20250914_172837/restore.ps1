param([string]\ = '.\logs\quarantine_20250914_172837')
Get-ChildItem -File -Recurse \ | ForEach-Object {
  \ = Join-Path (Resolve-Path '.').Path \.Name
  Move-Item -LiteralPath \.FullName -Destination \ -Force
}
