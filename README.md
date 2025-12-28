# Gloorbot (Distributed Lowe’s Deal Scraper)

This repo contains:
- A **Render-hosted coordinator** (`apps/coordinator`) that assigns scrape work and aggregates deals
- A **Windows-only 1-click worker** (`apps/worker`) that your friends can run: **Download → Install → Join**
- The **proven local Playwright scraper** (`PARALLEL/`) that the worker reuses to resist Akamai/WAF blocking

## Deploy (high level)

1. Push this repo to GitHub.
2. Deploy `apps/coordinator` on Render (Blueprint: `render.yaml`).
3. Build `WorkerSetup.exe` via GitHub Actions (`.github/workflows/worker-build.yml`) and host it (GitHub Release asset).
4. Set Render env var `WORKER_DOWNLOAD_URL` to your hosted `WorkerSetup.exe` URL.

## Where things live

- `apps/coordinator/` — FastAPI coordinator + website + SSE updates
- `apps/worker/` — Tkinter GUI worker, supervisor, slot workers, installer build scripts
- `PARALLEL/` — scraping engine (warmup, persistent profiles, pickup filter, pagination, anti-block cooldown)
- `tools/` — diagnostics and analysis scripts (non-production)

