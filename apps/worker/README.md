# Worker (Windows)

This is the **1-click** Windows worker app:
- Shows a GUI with **Join** / **Kill**
- Automatically pulls work from the Render coordinator
- Runs one or more scraping “slots” (browsers) and keeps the PC around **70–90%** utilization
- Only submits **≥50% off** deals to the coordinator

## Logs (installed worker)

The installed worker writes logs under:

- `%LOCALAPPDATA%\\GloorbotWorkerData\\logs`

Key files:

- `events_slot_<N>.jsonl` — high-level worker events (leased task, category start/done/error)
- `nav_slot_<N>.jsonl` — low-level navigation trace from `PARALLEL/scraper.py` with pagination stripped (`offset` removed)

## Dev run (not for friends)

```powershell
cd apps/worker
python -m venv .venv
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\python -m playwright install chromium
$env:GLOORBOT_COORDINATOR_URL="http://127.0.0.1:8000"
.\.venv\Scripts\python -m gloorbot_worker
```

## Akamai smoke test (manual)

```powershell
cd apps/worker
.\.venv\Scripts\python .\tools\akamai_smoke_test.py

# Optional: force system Chrome (requires Chrome installed)
$env:GLOORBOT_BROWSER_CHANNEL="chrome"
.\.venv\Scripts\python .\tools\akamai_smoke_test.py
```

## Packaging

The repo includes a GitHub Actions workflow + Inno Setup script (added later in this refactor)
to build `WorkerSetup.exe` that bundles everything (Python + deps + Playwright Chromium).
