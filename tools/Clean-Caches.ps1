[CmdletBinding()]
param(
  [string]$Root = (Get-Location).Path,
  [switch]$Apply,                          # якщо НЕ задано — DRY-RUN
  [string]$LogRoot = "$Root\temp\trash"
)
$ErrorActionPreference="Stop"; $DRY = -not $Apply
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sessionDir = Join-Path $LogRoot $stamp; New-Item -ItemType Directory -Force $sessionDir | Out-Null
$log = Join-Path $sessionDir "log.txt"; function Log($m){ Add-Content $log ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

$cacheDirs  = @("__pycache__", ".pytest_cache")
$cacheFiles = @("*.pyc","*.pyd","*.pyo")
$skip = "\\vendors\\|\\archive\\|\\\.git\\|\\temp\\trash\\"

Get-ChildItem $Root -Recurse -Directory -Force -EA SilentlyContinue |
  Where-Object { $cacheDirs -contains $_.Name -and $_.FullName -notmatch $skip } |
  ForEach-Object { if($DRY){ Log "[WhatIf] DIR  $($_.FullName)" } else { Remove-Item $_.FullName -Recurse -Force -EA SilentlyContinue; Log "Removed DIR  $($_.FullName)" } }

Get-ChildItem $Root -Recurse -File -Force -EA SilentlyContinue -Include $cacheFiles |
  Where-Object { $_.FullName -notmatch $skip } |
  ForEach-Object { if($DRY){ Log "[WhatIf] FILE $($_.FullName)" } else { Remove-Item $_.FullName -Force -EA SilentlyContinue; Log "Removed FILE $($_.FullName)" } }

Write-Output "Clean-Caches log: $log"
