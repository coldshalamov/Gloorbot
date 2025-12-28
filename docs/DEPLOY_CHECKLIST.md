# Gloorbot Distributed Scraper - Deploy Checklist

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         RENDER                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Coordinator (FastAPI)                                   │    │
│  │  - Dashboard + Live Deals (SSE)                         │    │
│  │  - /api/v1/lease/next (assigns work)                    │    │
│  │  - /api/v1/deals/bulk (receives ≥50% off deals)         │    │
│  │  - SQLite on persistent disk                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ▲                                     │
│                            │ HTTPS                               │
└────────────────────────────┼────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ Worker  │          │ Worker  │          │ Worker  │
   │  (PC1)  │          │  (PC2)  │          │  (PC3)  │
   └─────────┘          └─────────┘          └─────────┘
   Windows GUI           Windows GUI          Windows GUI
   + Playwright          + Playwright         + Playwright
```

---

## 1. Deploy Coordinator on Render

### Prerequisites
- GitHub repo pushed with `render.yaml` at root
- `apps/coordinator/data/urls.txt` contains store + category URLs

### Steps

1. **Connect repo to Render**
   - Go to https://dashboard.render.com
   - New → Blueprint → Connect your GitHub repo
   - Render will detect `render.yaml` and create the service

2. **Set environment variables** (Render Dashboard → gloorbot-coordinator → Environment)
   ```
   WORKER_DOWNLOAD_URL=<GitHub Release URL for WorkerSetup.exe>
   ```
   (Set this after building the worker - see step 2)

3. **Verify deployment**
   ```bash
   curl https://gloorbot-coordinator.onrender.com/healthz
   # Should return: {"ok": true, "utc": "..."}

   curl https://gloorbot-coordinator.onrender.com/api/v1/status
   # Should show tasks seeded from urls.txt
   ```

4. **Check dashboard**
   - Visit https://gloorbot-coordinator.onrender.com
   - Should show "Download Worker" button and status

---

## 2. Build Worker Installer (GitHub Actions)

### Trigger build

**Option A: Manual trigger**
1. Go to GitHub → Actions → "build-worker" workflow
2. Click "Run workflow"

**Option B: Tag-based trigger**
```bash
git tag worker-v0.1.0
git push origin worker-v0.1.0
```

### After build completes

1. Download `WorkerSetup.exe` from the workflow artifacts
2. Create a GitHub Release:
   - Go to Releases → Draft new release
   - Tag: `worker-v0.1.0`
   - Upload `WorkerSetup.exe` as release asset
3. Copy the direct download URL (right-click → Copy link address)
4. Set in Render:
   ```
   WORKER_DOWNLOAD_URL=https://github.com/YOUR_ORG/Gloorbot/releases/download/worker-v0.1.0/WorkerSetup.exe
   ```

---

## 3. Distribute to Volunteers

Share these instructions:

1. Visit: `https://gloorbot-coordinator.onrender.com`
2. Click **Download Worker**
3. Run `WorkerSetup.exe` (no admin required, installs to LocalAppData)
4. Click **Join** to start scraping
5. Click **Kill** to stop

The worker will:
- Auto-scale slots based on CPU/RAM (target: 70-90% utilization)
- Use persistent browser profiles (avoids re-login)
- Apply "Pickup Today" filter for local inventory
- Only submit deals that are ≥50% off

---

## Environment Variables Reference

### Coordinator (Render)
| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/var/data` | SQLite database location |
| `WORKER_DOWNLOAD_URL` | (none) | URL to WorkerSetup.exe |
| `DEAL_THRESHOLD` | `0.50` | Minimum discount (0.50 = 50% off) |
| `LEASE_SECONDS` | `900` | Task lease duration (15 min) |
| `ACTIVE_WINDOW_SECONDS` | `180` | Client considered "active" if seen within |

### Worker (Windows)
| Variable | Default | Description |
|----------|---------|-------------|
| `GLOORBOT_COORDINATOR_URL` | `https://gloorbot-coordinator.onrender.com` | Coordinator URL |
| `DEAL_THRESHOLD` | `0.50` | Local filter threshold |
| `BLOCK_COOLDOWN_SECONDS` | `300` | Wait time after Akamai block |

---

## Troubleshooting

### Coordinator Issues

**"WORKER_DOWNLOAD_URL not configured"**
- Set the env var in Render dashboard

**No tasks showing**
- Check `apps/coordinator/data/urls.txt` exists and has URLs
- Check Render logs for seeding errors

**Database issues after Render restart**
- SQLite is on persistent disk at `/var/data/coordinator.sqlite`
- If disk is missing, data is lost - redeploy will re-seed

### Worker Issues

**"Could not locate PARALLEL/ folder"**
- The PyInstaller build must include `--add-data "../../PARALLEL;PARALLEL"`
- Check the workflow ran successfully

**Browser not launching**
- Worker tries system Chrome first, falls back to bundled Playwright Chromium
- Check `%LOCALAPPDATA%\GloorbotWorker\logs\` for slot logs

**Blocked by Akamai**
- Worker auto-cools down for 5 minutes
- Check logs for "Access Denied" errors
- Consider reducing slots if blocked frequently

---

## Local Development

### Coordinator
```bash
cd apps/coordinator
pip install -r requirements.txt
uvicorn coordinator_app.main:app --reload --port 8000
# Visit http://localhost:8000
```

### Worker (dev mode)
```bash
cd apps/worker
pip install -e .
python -m gloorbot_worker
# Or set GLOORBOT_COORDINATOR_URL=http://localhost:8000
```
