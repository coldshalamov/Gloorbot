# Starts the Nucleus Brain MCP server as an SSE endpoint.
# Default endpoint: http://127.0.0.1:9090/nucleus/sse
#
# This is intended to be a singleton process so multiple agents (Codex, Claude Code,
# Antigravity) can coordinate via the same shared brain state.

[CmdletBinding()]
param(
  [string]$BrainPath = (Join-Path (Get-Location) ".brain"),
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 9090,
  [string]$Path = "/nucleus/sse",
  [switch]$Foreground
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  $here = Get-Location
  if (Test-Path (Join-Path $here ".git")) { return $here.Path }
  if (Test-Path (Join-Path $here ".brain")) { return $here.Path }
  return $here.Path
}

function Get-FastMcpExe {
  $candidate = "C:\Users\User\.claude\mcp-servers\nucleus\mcp-server-nucleus-main\.venv\Scripts\fastmcp.exe"
  if (Test-Path $candidate) { return $candidate }
  throw "fastmcp.exe not found at expected path: $candidate"
}

function Get-NucleusServerSpec {
  $candidate = "C:\Users\User\.claude\mcp-servers\nucleus\mcp-server-nucleus-main\src\mcp_server_nucleus\__init__.py"
  if (Test-Path $candidate) { return $candidate }
  throw "Nucleus server source not found at expected path: $candidate"
}

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

$repoRoot = Resolve-RepoRoot
$brainAbs = (Resolve-Path $BrainPath).Path

if (!(Test-Path $brainAbs)) {
  throw "Brain path does not exist: $brainAbs (expected a .brain directory)"
}

if (Test-PortListening -hostAddress $HostAddress -port $Port) {
  Write-Host "Nucleus appears to already be listening on $($HostAddress):$Port (not starting another instance)."
  exit 0
}

$fastmcpExe = Get-FastMcpExe
$serverSpec = Get-NucleusServerSpec

$args = @(
  "run",
  "--server-spec", $serverSpec,
  "--transport", "sse",
  "--host", $HostAddress,
  "--port", "$Port",
  "--path", $Path,
  "--no-banner",
  "--log-level", "WARNING"
)

$env:NUCLEAR_BRAIN_PATH = $brainAbs

$logDir = Join-Path $repoRoot ".brain\meta"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdoutLog = Join-Path $logDir "nucleus_sse_stdout.log"
$stderrLog = Join-Path $logDir "nucleus_sse_stderr.log"
$pidFile = Join-Path $logDir "nucleus_sse.pid"

if ($Foreground) {
  Write-Host "Starting Nucleus in foreground at http://$HostAddress`:$Port$Path"
  Write-Host "NUCLEAR_BRAIN_PATH=$brainAbs"
  & $fastmcpExe @args
  exit $LASTEXITCODE
}

$p = Start-Process -FilePath $fastmcpExe -ArgumentList $args -WindowStyle Minimized -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
$p.Id | Out-File -FilePath $pidFile -Encoding ascii

# Uvicorn/anyio can take a moment to bind; poll briefly.
$bound = $false
for ($i = 0; $i -lt 10; $i++) {
  Start-Sleep -Milliseconds 300
  if (Test-PortListening -hostAddress $HostAddress -port $Port) { $bound = $true; break }
}

if ($bound) {
  Write-Host "Started Nucleus SSE (pid=$($p.Id)) at http://$HostAddress`:$Port$Path"
  Write-Host "Logs: $stdoutLog ; $stderrLog"
  exit 0
}

Write-Host "Started process (pid=$($p.Id)) but port $Port is not listening yet."
Write-Host "Check logs: $stdoutLog ; $stderrLog"
exit 2
