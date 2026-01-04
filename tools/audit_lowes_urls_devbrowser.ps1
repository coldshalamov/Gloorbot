$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Get-DevBrowserPid {
  $conn = Get-NetTCPConnection -LocalPort 9222 -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $conn) { return $null }
  return $conn.OwningProcess
}

function Stop-DevBrowser {
  $serverPid = Get-DevBrowserPid
  if ($serverPid) {
    Write-Host "Stopping dev-browser server (PID $serverPid)..."
    Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
  }

  $cdp = Get-NetTCPConnection -LocalPort 9223 -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($cdp) {
    Write-Host "Stopping CDP browser (PID $($cdp.OwningProcess))..."
    Stop-Process -Id $cdp.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
  }
}

function Reset-DevBrowserProfile {
  $profile = "C:\Users\User\.codex\skills\dev-browser\profiles\browser-data"
  if (Test-Path $profile) {
    Write-Host "Resetting dev-browser profile: $profile"
    Remove-Item -Recurse -Force $profile
  }
  New-Item -ItemType Directory -Force -Path $profile | Out-Null
}

function Start-DevBrowser {
  $dev = "C:\Users\User\.codex\skills\dev-browser"
  if (-not (Test-Path $dev)) { throw "dev-browser directory missing: $dev" }

  if (Get-DevBrowserPid) {
    Write-Host "dev-browser already running."
    return
  }

  Write-Host "Starting dev-browser server..."
  # NOTE: Lowe's Akamai tends to block headless sessions. Keep HEADLESS=false.
  $env:HEADLESS = "false"
  Start-Process -FilePath "powershell.exe" -WorkingDirectory $dev -ArgumentList @(
    "-NoProfile",
    "-Command",
    "npm install; npx tsx scripts/start-server.ts"
  ) | Out-Null

  # Wait for server to come up
  for ($i = 0; $i -lt 30; $i++) {
    try {
      Invoke-WebRequest -Uri "http://localhost:9222" -UseBasicParsing -TimeoutSec 2 | Out-Null
      Write-Host "dev-browser ready."
      return
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  throw "dev-browser did not become ready on http://localhost:9222"
}

function Warmup-Lowes {
  $dev = "C:\Users\User\.codex\skills\dev-browser"
  Push-Location $dev
  try {
    $out = & npx tsx tmp\lowes-warmup-check.ts 2>&1
    $outText = ($out | Out-String).Trim()
    if ($outText -match '"afterHas0"\s*:\s*true' -and $outText -match '"ok"\s*:\s*true') {
      Write-Host "Warmup OK (_abck contains ~0~)."
      return
    }
    Write-Host "Warmup not OK; output:"
    Write-Host $outText
    throw "Warmup failed"
  } finally {
    Pop-Location
  }
}

function Build-CategoryOnlyList {
  param(
    [string]$SourceUrls = "C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apps\coordinator\data\urls.txt",
    [string]$OutFile = "C:\Users\User\Documents\GitHub\Telomere\Gloorbot\logs\coordinator_categories_only.txt"
  )

  if (-not (Test-Path $SourceUrls)) { throw "Missing source urls file: $SourceUrls" }
  $outDir = Split-Path -Parent $OutFile
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  Get-Content $SourceUrls | Where-Object { $_ -match "/pl/" } | Set-Content -Encoding UTF8 $OutFile
  $n = (Get-Content $OutFile | Measure-Object -Line).Lines
  Write-Host "Wrote category-only list: $OutFile ($n lines)"
}

function Run-Audit {
  param(
    [string]$ListFile,
    [string]$OutJsonl
  )

  $dev = "C:\Users\User\.codex\skills\dev-browser"
  Push-Location $dev
  try {
    & npx tsx tmp\audit-lowes-urls.ts --file $ListFile --limit 0 --out $OutJsonl --page lowes-cat-audit --resume true --requireAbck0 true
    return $LASTEXITCODE
  } finally {
    Pop-Location
  }
}

function Remove-404sFromList {
  param(
    [string]$AuditJsonl,
    [string]$SourceUrlsFile
  )

  if (-not (Test-Path $AuditJsonl)) { throw "Missing audit JSONL: $AuditJsonl" }
  if (-not (Test-Path $SourceUrlsFile)) { throw "Missing source URLs file: $SourceUrlsFile" }

  $notFound = New-Object System.Collections.Generic.HashSet[string]
  foreach ($line in Get-Content $AuditJsonl) {
    if (-not $line) { continue }
    try {
      $rec = $line | ConvertFrom-Json
    } catch { continue }
    if ($rec.kind -eq "not_found" -and $rec.url) {
      [void]$notFound.Add([string]$rec.url)
    }
  }

  $count = $notFound.Count
  Write-Host "Found $count URLs with kind=not_found"
  if ($count -eq 0) { return }

  $tmp = "$SourceUrlsFile.tmp"
  Get-Content $SourceUrlsFile | Where-Object { -not $notFound.Contains($_) } | Set-Content -Encoding UTF8 $tmp
  Move-Item -Force $SourceUrlsFile $SourceUrlsFile.bak
  Move-Item -Force $tmp $SourceUrlsFile
  Write-Host "Removed $count 404 URLs from $SourceUrlsFile (backup at $SourceUrlsFile.bak)"
}

# === Main ===
$repoRoot = "C:\Users\User\Documents\GitHub\Telomere\Gloorbot"
$sourceUrls = Join-Path $repoRoot "apps\coordinator\data\urls.txt"
$categoryList = Join-Path $repoRoot "logs\coordinator_categories_only.txt"
$auditOut = Join-Path $repoRoot "logs\dev_browser_category_full_audit.jsonl"

Build-CategoryOnlyList -SourceUrls $sourceUrls -OutFile $categoryList

$auditCompleted = $false
for ($attempt = 1; $attempt -le 50; $attempt++) {
  Start-DevBrowser

  Write-Host "Starting audit pass #$attempt (resume enabled)..."
  $exitCode = Run-Audit -ListFile $categoryList -OutJsonl $auditOut
  if ($exitCode -eq 0) {
    Write-Host "Audit completed."
    $auditCompleted = $true
    break
  }
  if ($exitCode -eq 3) {
    Write-Host "Audit stopped due to blocks/warmup failure; resetting profile and retrying..."
    Stop-DevBrowser
    Reset-DevBrowserProfile
    continue
  }
  throw "Audit failed with exit code $exitCode"
}

if (-not $auditCompleted) {
  throw "Audit did not complete after max attempts; not pruning URL lists."
}

# Only prune URLs from the source list if the audit fully covered the category list.
$expectedCount = (Get-Content $categoryList | Measure-Object -Line).Lines
$audited = New-Object System.Collections.Generic.HashSet[string]
foreach ($line in Get-Content $auditOut) {
  if (-not $line) { continue }
  try { $rec = $line | ConvertFrom-Json } catch { continue }
  if ($rec.url) { [void]$audited.Add([string]$rec.url) }
}
if ($audited.Count -ne $expectedCount) {
  throw "Audit output does not match expected count (expected=$expectedCount uniqueAudited=$($audited.Count)); not pruning URL lists."
}

Remove-404sFromList -AuditJsonl $auditOut -SourceUrlsFile $sourceUrls
Write-Host "Done."
