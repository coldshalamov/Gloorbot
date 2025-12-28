# Distributed Parallelizer (Render + Windows Workers)

Goal: friends can go to the coordinator site, click **Download**, install, click **Join**, and their PC starts scraping WA/OR Lowe’s stores and only submits **≥50% off** items.

## Coordinator (Render)

Path: `apps/coordinator`

What it does:
- Seeds the task universe from `apps/coordinator/data/urls.txt` (copied from `PARALLEL/urls.txt`)
- Issues **leases** for tasks (oldest `last_completed_at` first)
- Receives deals and serves a simple live dashboard

### Required env vars
- `WORKER_DOWNLOAD_URL` — direct URL to `WorkerSetup.exe`

### Recommended env vars
- `DATA_DIR` — persistent disk mount path (Blueprint uses `/var/data`)
- `LEASE_SECONDS` — default `900`
- `DEAL_THRESHOLD` — default `0.50`

## Worker (Windows)

Path: `apps/worker`

Behavior:
- GUI: **Join** starts scraping; **Kill** stops all slots.
- Supervisor keeps machine around **70–90%** utilization by starting/stopping slot workers every 90 seconds.
- Each slot worker:
  - Pulls a lease from the coordinator
  - Opens a headful Playwright browser with a persistent profile
  - Warmups on `lowes.com`, sets store, applies pickup filter, paginates category listings
  - Filters to **≥50% off** and submits only those deals

### Build `WorkerSetup.exe` (GitHub Actions)
- Workflow: `.github/workflows/worker-build.yml`
- Output artifact: `WorkerSetup.exe`

You should publish the artifact as a GitHub Release asset and set `WORKER_DOWNLOAD_URL` to that asset URL.
