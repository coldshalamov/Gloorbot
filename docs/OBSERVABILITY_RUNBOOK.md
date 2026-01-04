# Observability Runbook (Gloorbot → CheapSkater)

This runbook is designed to let you answer, end-to-end, **“are deals flowing?”** and **“why not?”** using:
- Render logs (Coordinator + CheapSkater)
- Health/status/debug endpoints (no secrets exposed)
- Correlation via a `batch_id` trace ID

---

## 0) Fast Checklist (10 seconds)

1. Coordinator: `GET /api/v1/status`
   - `integration.cheapskater_ingest_url_configured` must be `true`
   - `integration.latest_ingest` should update as workers send batches

2. CheapSkater: `GET /api/ingest/health`
   - `configured` must be `true`
   - `db_path` must be the same one dashboard uses

3. Render logs:
   - Coordinator: search for `[DEALS]` and `[FORWARD]`
   - CheapSkater: search for `[INGEST]`

---

## 1) Trace IDs (the core mechanic)

Every `/api/v1/deals/bulk` request gets a `batch_id`.

- Worker → Coordinator: `batch_id` is sent in the JSON body.
- Coordinator → CheapSkater: `batch_id` is forwarded in:
  - JSON body: `batch_id`
  - HTTP headers: `X-Gloorbot-Batch-Id`

This means you can correlate a single batch across:
- Coordinator `[DEALS] ... batch_id=...`
- Coordinator `[FORWARD] ... batch_id=...`
- CheapSkater `[INGEST] ... batch_id=...`

---

## 2) Coordinator Signals

### Logs (Render)
Search for:
- `[DEALS] batch_id=... received=... unique=... below_threshold=... upserted=...`
- `[FORWARD] ... attempting ...`
- `[FORWARD] ... ok accepted=...`
- `[FORWARD] ... failed status=...`

### Endpoints
- `GET /api/v1/status`
  - Shows `integration.*` (configured booleans + latest ingest event summary)
- `GET /api/v1/debug/ingest-events?limit=100`
  - Requires `DEBUG_API_TOKEN` and header `X-Debug-Token`
  - Shows recent ingest batches, forward status, errors
- `GET /api/v1/debug/deal-sources?store_id=...&product_url=...`
  - Requires `DEBUG_API_TOKEN` and header `X-Debug-Token`
  - Shows which `category_url` values are surfacing the same deal (helps debug duplicates)

### Retention (Coordinator debug tables)
Debug tables are pruned automatically (default `DEBUG_RETENTION_DAYS=3`):
- `ingest_events`
- `deal_sources`

---

## 3) CheapSkater Signals

### Logs (Render)
Search for:
- `[INGEST] batch_id=... client_id=... source=gloorbot deals=N db=/path/to/sqlite`
- `[INGEST] ... done accepted=N errors=M`

### Endpoints
- `GET /api/ingest/health`
  - Returns: `configured`, `db_path`, `db_exists`

### Persistence (critical)
If CheapSkater is using SQLite on Render, you must mount a **persistent disk** and set:
- `CHEAPSKATER_DB_PATH=/var/data/orwa_lowes.sqlite` (or similar)

If CheapSkater has no disk, deals can “disappear” after restarts/redeploys because the filesystem is ephemeral.

---

## 4) Diagnosing “Duplicates”

Coordinator uniqueness is defined as:
- `(store_id, product_url)` — same store + same product URL

Duplicates can come from:
- Overlapping category URLs (“vanities by brand” vs “vanities by size”)
- Multiple workers scraping overlapping tasks
- Natural re-surfacing of the same product across time (expected)

To see which category URLs are producing the duplicates:
1. Find a duplicate deal’s `store_id` and `product_url`
2. Call Coordinator:
   - `GET /api/v1/debug/deal-sources?store_id=...&product_url=...`

---

## 5) Worker Installer / Updates (current pipeline)

The worker is packaged via PyInstaller and shipped via an Inno Setup installer.

High-level release flow:
1. Build the worker binary: `apps/worker/build.ps1`
2. Build installer from `apps/worker/installer/worker.iss` (Inno Setup `ISCC.exe`)
3. Upload `WorkerSetup.exe` somewhere stable (e.g., GitHub Releases)
4. Set Coordinator env var:
   - `WORKER_DOWNLOAD_URL=<direct link to WorkerSetup.exe>`

Re-running the latest installer on a machine that already has the worker installed should update in-place
(same `AppId`, same install location).

---

## 6) Common Failure Modes

### A) Coordinator isn’t storing deals
- Symptom: `/api/v1/deals/bulk` returns 500 in Render request logs
- Fix: ensure Coordinator uses atomic upsert (idempotent) and is deployed

### B) Coordinator isn’t forwarding
- Symptom: Coordinator logs show `CHEAPSKATER_INGEST_URL not configured`
- Fix: set `CHEAPSKATER_INGEST_URL` on Coordinator service

### C) CheapSkater rejects forwarding (auth)
- Symptom: Coordinator `[FORWARD] failed status=401`
- Fix: match `CHEAPSKATER_INGEST_API_KEY` between services

### D) CheapSkater ingests but dashboard shows nothing
- Symptom: ingest 200 OK, but UI doesn’t change
- Common cause: ingest and dashboard writing/reading different DB paths
- Fix: both must use `CHEAPSKATER_DB_PATH` consistently

### E) Deals “disappear”
- Symptom: deals appear briefly, then vanish after restarts/deploys
- Fix: mount a persistent disk for CheapSkater and point DB to it

---

## 7) Copy/Paste Prompt (Optimized)

Use this when asking an agent (Codex/Claude/Antigravity) to debug end-to-end:

```
Goal: verify end-to-end deal flow Worker → Coordinator → CheapSkater → UI.
Do:
1) Pull last 100 Coordinator logs (request+app) and find [DEALS]/[FORWARD] lines (include batch_id).
2) Pull last 100 CheapSkater logs (request+app) and find [INGEST] lines (include batch_id).
3) Compare batch_id across both services to confirm forwarding+ingest.
4) Check /api/v1/status (Coordinator) integration flags and latest_ingest.
5) Check /api/ingest/health (CheapSkater) db_path/db_exists/configured.
Report: where the chain breaks and the exact error/status codes.
```
