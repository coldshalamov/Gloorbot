# Stops the Nucleus Brain MCP server started by start-nucleus-brain.ps1

[CmdletBinding()]
param(
  [string]$PidFile = (Join-Path (Get-Location) ".brain\\meta\\nucleus_sse.pid"),
  [switch]$Force
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $PidFile)) {
  Write-Host "No pid file found at: $PidFile"
  exit 0
}

$pidRaw = (Get-Content -Path $PidFile -ErrorAction Stop | Select-Object -First 1).Trim()
if ([string]::IsNullOrWhiteSpace($pidRaw)) {
  Write-Host "Pid file is empty: $PidFile"
  exit 1
}

$pid = [int]$pidRaw

try {
  $p = Get-Process -Id $pid -ErrorAction Stop
} catch {
  Write-Host "Process $pid not found; removing stale pid file."
  Remove-Item -Force $PidFile
  exit 0
}

try {
  if ($Force) {
    Stop-Process -Id $pid -Force
  } else {
    Stop-Process -Id $pid
  }
  Start-Sleep -Milliseconds 200
  Write-Host "Stopped Nucleus SSE process pid=$pid"
} finally {
  if (Test-Path $PidFile) { Remove-Item -Force $PidFile }
}

