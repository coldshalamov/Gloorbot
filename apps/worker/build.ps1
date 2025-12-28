$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path .venv)) {
  python -m venv .venv
}

.\.venv\Scripts\pip install -e .
.\.venv\Scripts\pip install pyinstaller==6.11.1

$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) "ms-playwright")
.\.venv\Scripts\python -m playwright install chromium

if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

.\.venv\Scripts\pyinstaller `
  --noconfirm `
  --clean `
  --name GloorbotWorker `
  --noconsole `
  --add-data "..\..\PARALLEL;PARALLEL" `
  --add-data "ms-playwright;ms-playwright" `
  src\gloorbot_worker\__main__.py

Write-Host "Built dist\GloorbotWorker\GloorbotWorker.exe"

