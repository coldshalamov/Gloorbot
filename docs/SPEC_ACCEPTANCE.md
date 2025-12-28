# Spec acceptance checklist (distributed parallelizer)

Use this to verify the repo meets the exact “Download → Install → Join” spec.

## Coordinator (Render)
- [ ] `/` renders with **Download Worker** button.
- [ ] `/download` redirects to valid `WorkerSetup.exe` (env var `WORKER_DOWNLOAD_URL` set).
- [ ] `/api/v1/status` returns task counts, active clients, and recent deals.
- [ ] Task seeding runs on startup using `apps/coordinator/data/urls.txt`.
- [ ] Lease allocation is **least-recently-completed first** and **atomic** (no duplicate leases).
- [ ] Leases expire and return to pool after `LEASE_SECONDS`.
- [ ] Deals are de-duplicated by `(store_id, product_url)` and update timestamps.
- [ ] Server stays up after restart; data persists using Render disk (`DATA_DIR`).

## Worker (Windows)
- [ ] User installs `WorkerSetup.exe` on a clean Windows machine (no Python installed).
- [ ] Worker GUI opens, shows **Join** and **Kill**.
- [ ] Click **Join**: worker connects to coordinator, begins scraping without further clicks.
- [ ] GUI shows **slots, CPU, memory**, and coordinator stats.
- [ ] Worker auto-spawns slots and keeps system ~70–90% utilization.
- [ ] Click **Kill**: all slots stop; GUI remains open.

## Scraping behavior
- [ ] Headful browser with persistent profile.
- [ ] Homepage warmup before navigation.
- [ ] Store context set (pickup availability reflects local store).
- [ ] Pickup filter applied and verified before pagination.
- [ ] Category pagination continues until completion or timeout.
- [ ] If blocked, worker cools down and resumes.

## Deals
- [ ] Only submit items with **price < was_price** and **≥50% off**.
- [ ] Deals include store_id, store_name, product_url, price, was_price, pct_off.
- [ ] Failed submissions backoff and retry (no tight loops).

## Build / Release
- [ ] GitHub Action builds `WorkerSetup.exe`.
- [ ] Release asset URL is set as `WORKER_DOWNLOAD_URL`.

