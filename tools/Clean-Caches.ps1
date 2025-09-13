param([switch]$WhatIf)

$excludeVendors = '*\vendors\*'
$excludeArchive = '*\archive\*'

$pycDirs = Get-ChildItem -Recurse -Directory -Filter "__pycache__" |
  Where-Object { $_.FullName -notlike $excludeVendors -and $_.FullName -notlike $excludeArchive }

$pycFiles = Get-ChildItem -Recurse -File -Include *.pyc,*.pyo,*.pyd -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notlike $excludeVendors -and $_.FullName -notlike $excludeArchive }

$pytest = Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" |
  Where-Object { $_.FullName -notlike $excludeVendors -and $_.FullName -notlike $excludeArchive }

"__pycache__: $($pycDirs.Count)"
"bytecode   : $($pycFiles.Count)"
".pytest_cache: $($pytest.Count)"

if ($WhatIf) { "Режим WhatIf: видалення лише симулюється."; return }

# 1) Спершу файли байткоду
$pycFiles | ForEach-Object {
  if (Test-Path $_.FullName) { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
}

# 2) Потім .pytest_cache
$pytest | ForEach-Object {
  if (Test-Path $_.FullName) { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

# 3) Наприкінці самі __pycache__
$pycDirs | ForEach-Object {
  if (Test-Path $_.FullName) { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

"Готово."
