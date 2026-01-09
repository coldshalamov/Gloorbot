# Gloorbot Project

## What This Project Is

**Gloorbot is a distributed web scraping system** that finds 50%+ markdown deals at Lowe's stores across WA and OR, then publishes them to a public website called Cheapskater.

## Critical Naming Confusion (READ THIS FIRST!)

**This is confusing and you MUST get it right:**

| Local Repo | GitHub Repo | Render Service Name | Render URL | What It Does |
|------------|-------------|---------------------|------------|--------------|
| `Gloorbot/` | `Telomere/Gloorbot` | **gloorbot-coordinator** | https://gloorbot-coordinator.onrender.com | Backend coordinator that assigns scraping tasks and aggregates deals |
| `CheapSkater-/` | `Telomere/CheapSkater-` | **Gloorbot** | https://cheapskater.onrender.com | Public-facing website that displays deals to users |

**The confusing part:**
- This repo (`Gloorbot`) deploys to Render as **"gloorbot-coordinator"**
- The `CheapSkater-` repo deploys to Render as **"Gloorbot"** (service name) at the URL `cheapskater.onrender.com`

**Why it's named this way:** Historical reasons. Just memorize it.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Worker (Downloadable EXE)                                       │
│ Built from: Gloorbot/apps/worker/                               │
│ Runs on: User's Windows computer                                │
│ Downloads from: GitHub Release (via "Download Worker" button)   │
│ Location: C:\Users\User\AppData\Local\GloorbotWorker           │
├─────────────────────────────────────────────────────────────────┤
│ What it does:                                                   │
│ 1. Scrapes Lowes.com product listings (with Playwright)        │
│ 2. Filters for 50%+ markdown deals                             │
│ 3. Submits deals to coordinator                                │
└─────────────────────────────────────────────────────────────────┘
                            ↓ POST /api/v1/deals/bulk
┌─────────────────────────────────────────────────────────────────┐
│ Coordinator (Render Service)                                    │
│ Repo: Gloorbot/apps/coordinator/                                │
│ Service Name: gloorbot-coordinator                              │
│ URL: https://gloorbot-coordinator.onrender.com                  │
├─────────────────────────────────────────────────────────────────┤
│ What it does:                                                   │
│ 1. Manages task queue (store × category combinations)          │
│ 2. Assigns work to connected workers                           │
│ 3. Receives deals from workers                                 │
│ 4. De-duplicates and validates deals                           │
│ 5. Stores deals in local SQLite                                │
│ 6. Forwards deals to Cheapskater website                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓ POST /api/ingest/deals
┌─────────────────────────────────────────────────────────────────┐
│ Cheapskater Website (Render Service)                            │
│ Repo: CheapSkater- (different repo!)                            │
│ Local Path: C:\Users\User\Documents\GitHub\Telomere\CheapSkater-│
│ Service Name: Gloorbot (yes, really!)                           │
│ URL: https://cheapskater.onrender.com                           │
├─────────────────────────────────────────────────────────────────┤
│ What it does:                                                   │
│ 1. Receives deals via API from coordinator                     │
│ 2. Stores in SQLite at /var/data/orwa_lowes.sqlite            │
│ 3. Displays deals on public website                           │
│ 4. Users browse and find deals                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Lowes.com
    ↓ (Playwright scraping)
Worker EXE (user's computer)
    ↓ (filters 50%+ deals)
    ↓ POST /api/v1/deals/bulk
Coordinator (gloorbot-coordinator.onrender.com)
    ↓ (validates & deduplicates)
    ↓ POST /api/ingest/deals
Cheapskater Website (cheapskater.onrender.com, service name "Gloorbot")
    ↓ (stores in SQLite)
Public Website UI (users see deals)
```

## Project Structure

```
Gloorbot/
├── PARALLEL/                    # Local testing scraper
│   ├── scraper.py              # Core Playwright scraping logic
│   ├── orchestrator.py         # Multi-worker manager
│   ├── worker.py               # Per-store wrapper
│   ├── urls.txt                # 49 stores × 605 categories
│   └── output/                 # Scraped product JSONL files
│
├── apps/
│   ├── worker/                 # Distributed worker (builds to EXE)
│   │   ├── src/gloorbot_worker/
│   │   │   ├── slot_worker.py  # Main worker loop, deal filtering
│   │   │   ├── api.py          # Coordinator API client
│   │   │   └── parallel.py     # Imports PARALLEL scraper
│   │   └── pyproject.toml
│   │
│   └── coordinator/            # Backend service (FastAPI)
│       ├── coordinator_app/
│       │   ├── web.py          # API endpoints, deal forwarding
│       │   └── models.py       # SQLAlchemy models
│       └── pyproject.toml
│
├── .github/workflows/
│   └── worker-build.yml        # Builds worker EXE, creates GitHub release
│
├── docs/                       # Documentation
├── logs/                       # Runtime logs (gitignored)
└── CLAUDE.md                   # This file
```

## Key Technical Decisions

### Why Playwright?
Lowe's uses heavy JavaScript rendering and Akamai bot detection. Playwright with stealth plugins is the only reliable way to scrape without blocks.

### Why 50% Threshold?
Lower discounts aren't interesting to users. The filter is enforced in two places (defense-in-depth):
- Worker: `apps/worker/src/gloorbot_worker/slot_worker.py:364`
- Coordinator: `apps/coordinator/coordinator_app/web.py:629`

### Why SQLite?
- Simple, no external dependencies
- Fast enough for this use case
- Easy to back up (single file)

### Why Separate Repos?
Historical. `CheapSkater-` existed first as a standalone website, then `Gloorbot` was created to feed it data.

## Development Workflow

### Local Testing (PARALLEL folder)
```bash
cd PARALLEL
python orchestrator.py  # Run full scrape with 4 workers
# or
python worker.py 0      # Test single store
```

Output goes to `PARALLEL/output/*.jsonl`

### Building the Worker EXE
1. Make code changes in `apps/worker/`
2. Commit and push to GitHub
3. Create a new tag: `git tag v0.11.6 && git push origin v0.11.6`
4. GitHub Action automatically:
   - Runs regression tests
   - Builds PyInstaller EXE (includes Playwright Chromium)
   - Creates Inno Setup installer
   - Publishes GitHub Release with `WorkerSetup.exe`

### Deploying Coordinator
Coordinator auto-deploys from `main` branch to Render.

### Deploying Cheapskater
Go to the `CheapSkater-` repo and deploy from there (different repo!).

## Environment Variables

### Worker (runs on user's computer)
Optional diagnostics:
- `GLOORBOT_DEAL_DIAGNOSTICS=1` - Log why deals are rejected (`logs/deal_diagnostics/`)
- `GLOORBOT_PRICE_DIAGNOSTICS=1` - Log price extraction details (`logs/price_diagnostics/`)
- `GLOORBOT_NAVLOG_PATH=logs/nav.jsonl` - Log all page navigations

### Coordinator (Render service: gloorbot-coordinator)
**Required:**
- `CHEAPSKATER_INGEST_URL` - `https://cheapskater.onrender.com/api/ingest/deals`
- `CHEAPSKATER_INGEST_API_KEY` - Secret API key for authentication

**Optional:**
- `DATABASE_URL` - SQLite path (default: `coordinator.sqlite`)
- `DEBUG_API_TOKEN` - Token for debug endpoints
- `DEBUG_RETENTION_DAYS` - How long to keep debug data (default: 3)

### Cheapskater (Render service: Gloorbot, URL: cheapskater.onrender.com)
**Critical:**
- `CHEAPSKATER_DB_PATH` - **MUST be `/var/data/orwa_lowes.sqlite`** (the live database)

**Common mistake:** Setting this to an old database like `/var/data/orwa_lowes_CLEAN_2026-01-06.sqlite` causes deals to be saved but not displayed on the website.

## Known Issues & Gotchas

### Issue: Deals aren't showing up on Cheapskater website
**Symptoms:** Coordinator logs show deals being forwarded, Cheapskater logs show `accepted=1`, but website shows 0 deals.

**Cause:** `CHEAPSKATER_DB_PATH` environment variable on Render service "Gloorbot" is set to an old database file instead of the live one.

**Fix:**
1. Go to Render dashboard
2. Find service **"Gloorbot"** (yes, the confusing name)
3. Environment tab
4. Change `CHEAPSKATER_DB_PATH` to `/var/data/orwa_lowes.sqlite`
5. Save (service will restart)

### Issue: Worker EXE changes don't take effect
**Cause:** GitHub tag wasn't updated, so the release still has the old build.

**Fix:**
1. Verify latest tag: `gh release list --limit 1`
2. Check tag timestamp vs. your code changes
3. Create new tag if needed: `git tag v0.11.X && git push origin v0.11.X`
4. Wait for GitHub Action to complete (~10 minutes)
5. Re-download worker from new release

### Issue: Price extraction returns empty `was_price`
**Cause:** Lowe's changed their HTML selectors.

**Fix:** Update `PARALLEL/scraper.py` in the `extract_prices_from_card()` function with new selectors. The scraper has 4 fallback strategies (JSON-LD, canonical selectors, aria-labels, text blob inference).

### Issue: Akamai blocks workers
**Symptoms:** Browser gets "Access Denied" page or suspicious challenges.

**Prevention:**
- Worker includes stealth plugins
- Human-like delays between requests (2-4 seconds)
- Randomized mouse movements during warmup
- Never run multiple workers on same IP (use different computers)

## Current Plan

- [x] Build working distributed scraper
- [x] Deploy coordinator to Render
- [x] Create worker installer with GitHub Actions
- [ ] Fix Cheapskater database path (manual Render config change needed)
- [ ] Monitor for Akamai blocks and adjust stealth tactics
- [ ] Scale to more workers/computers if needed

## Debugging Checklist

When deals aren't appearing:

1. **Check coordinator logs** (gloorbot-coordinator service):
   - Look for `POST /api/v1/deals/bulk` requests
   - Look for `[FORWARD]` log lines showing forwarding to Cheapskater

2. **Check Cheapskater logs** (Gloorbot service at cheapskater.onrender.com):
   - Look for `[INGEST]` log lines
   - Verify `db=/var/data/orwa_lowes.sqlite` (NOT an old dated file)

3. **Check worker diagnostics** (if enabled):
   - `logs/deal_diagnostics/` - see why deals are rejected
   - `logs/price_diagnostics/` - see price extraction details

4. **Verify worker version**:
   - Check GitHub release timestamp
   - Ensure workers downloaded latest installer

## Success Criteria

You know it's working when:

✅ Coordinator logs show `POST /api/v1/deals/bulk` with `accepted > 0`

✅ Coordinator logs show `[FORWARD] ... ok accepted=X`

✅ Cheapskater logs show `[INGEST] ... accepted=X` with correct `db=/var/data/orwa_lowes.sqlite`

✅ Cheapskater website (https://cheapskater.onrender.com) displays new deals

✅ Workers complete tasks without getting blocked by Akamai
