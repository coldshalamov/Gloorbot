# Coordinator (Render)

This is the Render-hosted coordinator:
- Hosts a simple website (Download button + live deals table)
- Assigns work leases to worker PCs (least recently scraped first)
- Aggregates and serves 50%+ off deals
- Seeds tasks from `apps/coordinator/data/urls.txt` (copied from `PARALLEL/urls.txt`)

## Local run

```powershell
cd apps/coordinator
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:WORKER_DOWNLOAD_URL="https://example.com/WorkerSetup.exe"
.\.venv\Scripts\python -m uvicorn coordinator_app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Render deploy

- Create a Render Web Service from this repo.
- Root Directory: `apps/coordinator`
- Dockerfile: `apps/coordinator/Dockerfile`
- Set env var `WORKER_DOWNLOAD_URL` to your GitHub Release asset URL.
- Add a persistent disk and set `DATA_DIR` to its mount path (recommended).
