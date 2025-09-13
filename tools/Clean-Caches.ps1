param([switch]$WhatIf)

Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
  $excludeVendors = "*\vendors\*"
  $excludeArchive = "*\archive\*"

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

  $pycFiles | ForEach-Object { if (Test-Path $_.FullName) { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue } }
  $pytest   | ForEach-Object { if (Test-Path $_.FullName) { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue } }
  $pycDirs  | ForEach-Object { if (Test-Path $_.FullName) { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue } }

  "Готово."
}
finally {
  Pop-Location
}
