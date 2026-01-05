# Pipeline Health & Debug Plan (Gloorbot → Coordinator → CheapSkater)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Verify that scraping is progressing across categories/stores without getting stuck (especially on `/c/` URLs), and that deals (price + image) reliably flow through coordinator into the disk-backed CheapSkater DB.

**Architecture:** Worker leases tasks from Render coordinator, scrapes Lowe’s `/pl/` category listings, submits filtered deals to coordinator, and coordinator forwards accepted deals to CheapSkater ingest. CheapSkater persists to SQLite at the Render Disk mount (`/var/data/...`).

**Tech Stack:** Python (FastAPI on Render), Playwright (worker/scraper), SQLite (coordinator + CheapSkater), Render Disks, JSONL diagnostics logs.

---

### Task 1: Confirm Render services and IDs (ground truth)

**Tools:** Render MCP (`list_services`)

**Expected services**
- Coordinator (Render): `gloorbot-coordinator` (service slug)
- CheapSkater (Render): `cheapskater` (service slug)

**Step 1: List services**
- Run: Render MCP `list_services`
- Verify the two services exist and record `serviceId` values.

**Step 2: Verify disk mounts are present**
- For each service, inspect `serviceDetails.disk.mountPath` is `/var/data`
- Expected: disk attached for both coordinator + cheapskater.

---

### Task 2: Verify deploy succeeded (coordinator + cheapskater)

**Files:** none

**Step 1: Check latest deploys**
- Run: Render MCP `list_deploys(serviceId=<id>)` for each service
- Verify latest deploy is `live`/successful (no failed status).

**Step 2: Pull recent logs around startup**
- Run: Render MCP `list_logs(resource=[serviceId], type=['app','build'], direction='backward', startTime=<last 1–2h>)`
- Look for: startup exceptions, missing env vars, DB path errors, seed/prune logs.

---

### Task 3: Confirm coordinator → cheapskater forwarding is alive

**Tools:** HTTP GET from any machine, Render logs

**Step 1: Coordinator health/status**
- `GET https://gloorbot-coordinator.onrender.com/healthz` → should return `{"ok": true, ...}`
- `GET https://gloorbot-coordinator.onrender.com/api/v1/status`
  - Expect:
    - `integration.cheapskater_ingest_url_configured=true`
    - `integration.cheapskater_ingest_api_key_configured=true`
    - `integration.latest_ingest.forward_status_code=200` during active flow

**Step 2: CheapSkater ingest health (disk-backed DB)**
- `GET https://cheapskater.onrender.com/api/ingest/health`
  - Expect:
    - `configured=true`
    - `db_path` under `/var/data/...`
    - `db_exists=true`

**Step 3: Validate deals visible via API**
- `GET https://cheapskater.onrender.com/api/clearance`
  - Expect JSON with `items[]` including `image_url`, `price`, `price_was`, `pct_off`.

---

### Task 4: Prove the `/c/` URL problem cannot reappear

**Files:** `apps/coordinator/coordinator_app/web.py`, `apps/coordinator/coordinator_app/seed.py`, `PARALLEL/scraper.py`, `apps/worker/src/gloorbot_worker/slot_worker.py`

**Step 1: Confirm coordinator will not lease `/c/` tasks**
- Ensure `lease_next` filter includes `Task.category_url.not_like("%/c/%")`.

**Step 2: Confirm startup seed prunes legacy `/c/` tasks**
- Ensure seed deletes tasks where `category_url LIKE '%/c/%'` and logs `pruned_tasks_c_category`.

**Step 3: Turn on debug endpoint to measure `/c/` tasks (optional but recommended)**
- Set Render env var on coordinator:
  - `DEBUG_API_TOKEN=<random secret>`
- Then call:
  - `GET /api/v1/debug/task-url-stats` with header `x-debug-token: <token>`
  - Expect: `tasks_c_count=0` and `tasks_c_leased_count=0`

**Step 4: Confirm scraper aborts on `/pl/` → `/c/` redirects**
- Ensure `PARALLEL/scraper.py` raises on redirect to `/c/` during:
  - initial `category_goto`
  - pagination `page.goto(page_url)`

**Step 5: Worker failsafe**
- Ensure worker logs `task_abandoned_non_pl` and stops retrying a bad task indefinitely.

---

### Task 5: 20-minute worker smoke run with evidence (recommended)

**Files:** local machine logs under `%LOCALAPPDATA%\\GloorbotWorkerData\\logs`

**Step 1: Start worker and let it run 20 minutes**

**Step 2: Inspect per-slot logs**
- `events_slot_<N>.jsonl`
  - Expect repeating `lease_acquired` → `category_start` → `category_done`
  - Watch for excessive `category_error` or repeated same `category_url`
- `nav_slot_<N>.jsonl`
  - Expect `pickup_applied`, pagination navigations
  - Any `redirect_to_c` is actionable; worker should not spin forever on it

**Step 3: Correlate with coordinator**
- During the run, re-check coordinator `/api/v1/status`:
  - `clients.active > 0`
  - `tasks.completed_last_hour` increasing
  - `latest_ingest.forward_status_code=200` and `forwarded_count>0` for active batches

---

### Task 6: Price/outlier sanity checks

**Goal:** prevent “$1000 item shows $4” false positives.

**Step 1: Scraper-side heuristic**
- Ensure fallback does not use `min(vals)` and instead chooses a plausible `now/was` pair.

**Step 2: Worker-side filter**
- Ensure the worker drops obvious parse noise for high-ticket items (e.g. `was_price >= 200` and `price_now <= 10`).

**Step 3: If unsure, add a “suspicious deals” log**
- (Optional) Log dropped “suspicious” candidates for later review instead of silently dropping.

