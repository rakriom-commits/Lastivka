param(
  [string]$Root="C:\Lastivka\gateway\cloud_mailbox",
  [string]$TaskName="verify1.task.json"
)

$inbox = Join-Path $Root 'inbox'
$outbox = Join-Path $Root 'outbox'
$archive = Join-Path $Root 'archive'
$quarantine = Join-Path $Root 'quarantine'
$log = Join-Path $Root 'logs\gateway.log'
$allowFlag = "C:\Lastivka\ALLOW_APPLY.flag"

New-Item $outbox,$archive,$quarantine,(Split-Path $log) -ItemType Directory -Force | Out-Null
function W-Log([string]$msg){
  $ts=(Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  "$ts $msg" | Add-Content $log
}

function Get-PayloadHash([string]$path){
  $txt  = Get-Content $path -Raw -Encoding UTF8
  $obj  = $txt | ConvertFrom-Json -ErrorAction Stop
  $obj.PSObject.Properties.Remove("sha256") | Out-Null
  $payload = $obj | ConvertTo-Json -Depth 20 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
  $sha   = [System.Security.Cryptography.SHA256]::Create()
  (($sha.ComputeHash($bytes)) | ForEach-Object { param(
  [string]$Root="C:\Lastivka\gateway\cloud_mailbox",
  [string]$TaskName="verify1.task.json"
)

$inbox = Join-Path $Root 'inbox'
$outbox = Join-Path $Root 'outbox'
$archive = Join-Path $Root 'archive'
$quarantine = Join-Path $Root 'quarantine'
$log = Join-Path $Root 'logs\gateway.log'
$allowFlag = "C:\Lastivka\ALLOW_APPLY.flag"

New-Item $outbox,$archive,$quarantine,(Split-Path $log) -ItemType Directory -Force | Out-Null
function W-Log([string]$msg){
  $ts=(Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  "$ts $msg" | Add-Content $log
}

function Get-PayloadHash([string]$path){
  # Детерміноване хешування: JSON -> remove sha256 -> JSON -> SHA256
  $txt  = Get-Content $path -Raw -Encoding UTF8
  $obj  = $txt | ConvertFrom-Json -ErrorAction Stop
  $obj.PSObject.Properties.Remove('sha256') | Out-Null
  $payload = $obj | ConvertTo-Json -Depth 20
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
  $sha   = [System.Security.Cryptography.SHA256]::Create()
  (($sha.ComputeHash($bytes)) | ForEach-Object { $_.ToString("x2") }) -join ''
}

$tf = Join-Path $inbox $TaskName
if(!(Test-Path $tf)){
  Write-Host "NO TASK: $tf"
  exit 1
}

try {
  $task = Get-Content $tf -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
} catch {
  W-Log "bad json: $TaskName"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  exit 2
}

if($task.sender -ne 'sofia'){
  W-Log "sender not allowed: $($task.sender)"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  exit 3
}

$payloadHash = Get-PayloadHash $tf
$hashOk = ($task.sha256 -as [string]) -and ($task.sha256.ToLower() -eq $payloadHash.ToLower())

# ACK
$ackPath = Join-Path $outbox ("{0}.ack.json" -f $task.id)
@{
  id=$task.id; ts=(Get-Date).ToString("s"); receiver="lastivka";
  status="received"; version="gateway-1.0"; hash_ok=$hashOk
} | ConvertTo-Json -Depth 6 | Out-File $ackPath -Encoding UTF8

if(-not $hashOk){
  W-Log "hash mismatch -> quarantine: $($task.id)"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  Write-Host "HASH MISMATCH -> QUARANTINE"
  exit 4
}

$dry = -not (Test-Path $allowFlag) -or ($task.limits.mode -ne 'safe')
Start-Sleep -Seconds ([math]::Min(($task.limits.max_runtime_s -as [int]), 5))

# STATUS
$statusPath = Join-Path $outbox ("{0}.status.json" -f $task.id)
@{
  id=$task.id; ts=(Get-Date).ToString("s"); phase="done";
  result=@{ ok=$true; summary=("одноразовий тест (dryRun={0})" -f $dry) };
  artifacts=@(); guard=@{ apply_used=(! $dry); writes=0 }
} | ConvertTo-Json -Depth 6 | Out-File $statusPath -Encoding UTF8

# ARCHIVE
$day=(Get-Date).ToString("yyyyMMdd")
$archDir=Join-Path $archive $day
New-Item $archDir -ItemType Directory -Force | Out-Null
Move-Item $tf (Join-Path $archDir $TaskName) -Force

Write-Host "DONE: ACK+STATUS created; task archived to $archDir"
.ToString("x2") }) -join ""
}) -join ''
}

$tf = Join-Path $inbox $TaskName
if(!(Test-Path $tf)){
  Write-Host "NO TASK: $tf"
  exit 1
}

try {
  $task = Get-Content $tf -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
} catch {
  W-Log "bad json: $TaskName"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  exit 2
}

if($task.sender -ne 'sofia'){
  W-Log "sender not allowed: $($task.sender)"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  exit 3
}

$payloadHash = Get-PayloadHash $tf
$hashOk = ($task.sha256 -as [string]) -and ($task.sha256.ToLower() -eq $payloadHash.ToLower())

# ACK
$ackPath = Join-Path $outbox ("{0}.ack.json" -f $task.id)
@{
  id=$task.id; ts=(Get-Date).ToString("s"); receiver="lastivka";
  status="received"; version="gateway-1.0"; hash_ok=$hashOk
} | ConvertTo-Json -Depth 6 | Out-File $ackPath -Encoding UTF8

if(-not $hashOk){
  W-Log "hash mismatch -> quarantine: $($task.id)"
  Move-Item $tf (Join-Path $quarantine $TaskName) -Force
  Write-Host "HASH MISMATCH -> QUARANTINE"
  exit 4
}

$dry = -not (Test-Path $allowFlag) -or ($task.limits.mode -ne 'safe')
Start-Sleep -Seconds ([math]::Min(($task.limits.max_runtime_s -as [int]), 5))

# STATUS
$statusPath = Join-Path $outbox ("{0}.status.json" -f $task.id)
@{
  id=$task.id; ts=(Get-Date).ToString("s"); phase="done";
  result=@{ ok=$true; summary=("одноразовий тест (dryRun={0})" -f $dry) };
  artifacts=@(); guard=@{ apply_used=(! $dry); writes=0 }
} | ConvertTo-Json -Depth 6 | Out-File $statusPath -Encoding UTF8

# ARCHIVE
$day=(Get-Date).ToString("yyyyMMdd")
$archDir=Join-Path $archive $day
New-Item $archDir -ItemType Directory -Force | Out-Null
Move-Item $tf (Join-Path $archDir $TaskName) -Force

Write-Host "DONE: ACK+STATUS created; task archived to $archDir"

