# Quick status check for the Nucleus Brain MCP SSE server.

[CmdletBinding()]
param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 9090,
  [string]$Path = "/nucleus/sse",
  [string]$PidFile = (Join-Path (Get-Location) ".brain\\meta\\nucleus_sse.pid")
)

$ErrorActionPreference = "Stop"

function Test-PortListening([string]$hostAddress, [int]$port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($hostAddress, $port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(250)
    if ($ok -and $client.Connected) { $client.Close(); return $true }
    $client.Close(); return $false
  } catch {
    return $false
  }
}

$listening = Test-PortListening -hostAddress $HostAddress -port $Port

Write-Host "Endpoint: http://$HostAddress`:$Port$Path"
Write-Host "Listening: $listening"

if (Test-Path $PidFile) {
  $procId = (Get-Content -Path $PidFile | Select-Object -First 1).Trim()
  if ($procId) {
    try {
      $p = Get-Process -Id ([int]$procId) -ErrorAction Stop
      Write-Host "PID: $procId ($($p.ProcessName))"
    } catch {
      Write-Host "PID file exists but process not found: $procId"
    }
  }
} else {
  Write-Host "PID file not found: $PidFile"
}

exit 0
