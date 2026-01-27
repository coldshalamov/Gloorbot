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

## Architecture Overview

```
                                    ┌───────────────────────┐
                                    │   Lowe's Website      │
                                    └──────────┬────────────┘
                                               │ Scrape (Playwright)
                                               ▼
┌────────────────────────────────────────────────────────┐
│  THE SWARM (Distributed Workers)                       │
│                                                        │
│  [Worker 1] [Worker 2] ... [Worker N]                  │
│                                                        │
│  - Downloaded from Render Coord website                │
│  - Run by users on their PCs                           │
│  - "Gloorbot Worker" app (EXE)                         │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ POST /api/v1/deals/bulk
                            ▼
┌────────────────────────────────────────────────────────┐
│  COORDINATOR (Backend Service)                         │
│                                                        │
│  - URL: gloorbot-coordinator.onrender.com              │
│  - Assigns Tasks (Store x Category)                    │
│  - Validates & Deduplicates Deals                      │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ POST /api/ingest/deals
                            ▼
┌────────────────────────────────────────────────────────┐
│  CHEAPSKATER (Public Website)                          │
│                                                        │
│  - URL: cheapskater.onrender.com                       │
│  - Displays deals to the world                         │
└────────────────────────────────────────────────────────┘
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

## The "Gloorbot Swarm" Narrative (READ THIS!)

**This project is a distributed scraping system** (a "Swarm"). 
Users join the swarm by downloading the **Worker** application and running it on their PC.

**The User Journey:**
1. User visits the **Coordinator** website (`https://gloorbot-coordinator.onrender.com`).
2. User clicks **"Download Worker"**.
3. User installs `WorkerSetup.exe` (built via GitHub Actions).
4. User runs "Gloorbot Worker".
5. The Worker connects to the swarm, leases tasks, and scrapes Lowe's.
6. Deals are sent to the Coordinator -> Cheapskater Website (`https://cheapskater.onrender.com`).

## Project Structure (What matters vs. Legacy)

```
Gloorbot/
├── apps/                       # ✅ PRODUCTION CODE
│   ├── worker/                 # The distributed client (builds to EXE)
│   │   ├── src/gloorbot_worker/ # Main application logic
│   │   └── installer/          # Inno Setup script for WorkerSetup.exe
│   │
│   └── coordinator/            # The backend brain (FastAPI on Render)
│       └── coordinator_app/    # API, Task Queue, Deal Aggregation
│
├── .github/workflows/          # ✅ BUILD SYSTEM
│   └── worker-build.yml        # CI/CD: Builds WorkerSetup.exe on tag v*
│
├── PARALLEL/                   # ⚠️ SHARED LIBRARY / LEGACY
│   ├── scraper.py              # Core Playwright logic (imported by Worker!)
│   ├── urls.txt                # Canonical Seed List
│   └── ...                     # Other files here are mostly local dev tools
│
├── verifications/              # ✅ TEST SUITE
│   └── run_suite.py            # Regression tests run by CI
│
├── logs/                       # 🗑️ IGNORED (Runtime logs)
│
└── [Everything Else]           # 🛑 LEGACY / DEV SCRIPTS
    ├── *.py (root)             # One-off scripts, old experiments, etc.
    ├── GloorbotWorker.zip      # 📦 Build Artifact (Output of GitHub Actions)
    └── ...
```

**Key Takeaway**: If you are fixing the "Product", you are working in `apps/worker` or `apps/coordinator`. If you are fixing the "Scraping Logic", you are working in `PARALLEL/scraper.py`. Everything else is likely noise.

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

## Agent Instructions

**⚠️ CRITICAL: Do NOT auto-commit or push without explicit user request.**

Claude will make changes but NOT commit them automatically. The user must explicitly ask "commit this" or similar. This prevents rebuilding the Render service 30 times a day from unsolicited commits.

Changes stay in working tree until user asks. Only commit when explicitly requested.

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

---

## Performance Tuning Guide

### Overview

The worker includes a **Performance Settings** system with GUI controls accessible via the "Settings" button. These allow you to tune speed vs. detection risk.

### GUI Settings Dialog

Click **Settings** (when worker is stopped) to open the Performance Tuning dialog with three tabs:

1. **Timing** - Browser pool size and navigation/click delays
2. **Resources** - Resource blocking (images, fonts, media, analytics)
3. **Presets** - Quick presets from Conservative to Ultra-Aggressive

### Presets

| Preset | Speed | Block Risk | Use Case |
|--------|-------|------------|----------|
| **Conservative** | Slow | Very Low | Getting blocked frequently |
| **Balanced** | Medium | Low | Default, proven reliable |
| **Aggressive** | Fast | Medium | Good residential IPs |
| **Ultra Aggressive** | Maximum | High | Excellent IPs only |

### Key Settings

#### Browser Pool
- **Fixed Browser Count**: Set to 5 for predictable performance (0 = dynamic scaling)
- **Dynamic Mode**: Scales based on CPU/memory (70-90% thresholds)
- Fixed mode prevents thrashing from constant browser open/close

#### Timing Delays
- **Nav Delay**: Time after loading pages (default 1.5-3.9s)
- **Click Delay**: Time before clicking elements (default 0.1-0.4s)
- **Inter-Task Delay**: Time between finishing tasks (default 2.0-4.55s)

**WARNING**: Setting delays too low triggers Akamai's "inhuman speed" detection!

#### Resource Blocking
- **Block Images**: 60-70% bandwidth savings, DOM still renders structure
- **Block Fonts**: 5-10% bandwidth savings, minor visual difference
- **Block Media**: Safe, rarely used on Lowe's
- **Block Analytics**: Blocks tracking (except Akamai /_sec/ scripts)

**CRITICAL**: NEVER block `/_sec/` scripts - this is Akamai's bot detection!

#### Browser Optimizations
- **Disable GPU**: Faster on low-end machines
- **Memory Pressure Off**: Prevents OOM crashes
- **Disable Background Networking**: Reduces idle traffic

### What Gets You Blocked

| Signal | Detection | Block Speed | Mitigation |
|--------|-----------|-------------|------------|
| **Headless** | navigator.webdriver | Instant | NEVER run headless |
| **Datacenter IP** | IP reputation | Instant | Use residential proxies |
| **Too Fast** | Timing analysis | ~30s | Use Conservative preset |
| **Block /_sec/** | Missing Akamai cookie | Instant | Never block Akamai scripts |
| **Stealth Scripts** | Fingerprint mismatch | Fast | Don't use playwright-stealth |

### Safe Optimizations (Won't Trigger Akamai)

✅ Block images (but keep DOM structure)
✅ Block fonts, media, analytics (except Akamai)
✅ Reduce viewport size (1280x720 vs 1440x900)
✅ Disable GPU/background networking
✅ Fixed browser pool (prevents open/close thrashing)
✅ Memory pressure off (prevents crashes)

### Dangerous Optimizations (May Trigger Akamai)

⚠️ Very short navigation delays (<1s)
⚠️ Very short click delays (<0.05s)
⚠️ Blocking CSS or JavaScript
⚠️ Running more than 5-6 browsers on same IP
⚠️ Headless mode (instant block)
⚠️ playwright-stealth injection

### Recommended Settings for Testing Speed

To find the fastest safe settings:

1. Start with **Balanced** preset
2. Set **Fixed Browser Count** to 5
3. Enable **Block Images** and **Block Fonts**
4. Run for 30 minutes, check for blocks
5. If no blocks, try **Aggressive** preset
6. If getting blocked, switch to **Conservative**

### Settings File Location

Settings are persisted to:
```
%LOCALAPPDATA%\GloorbotWorkerData\config\performance_settings.json
```

You can edit this file directly or use the GUI.

### Environment Variable Overrides

These env vars can override settings (useful for testing):

```bash
GLOORBOT_FIXED_BROWSER_COUNT=5
GLOORBOT_MAX_BROWSERS=5
GLOORBOT_CLICK_DELAY_MIN=0.1
GLOORBOT_CLICK_DELAY_MAX=0.4
GLOORBOT_NAV_DELAY_MIN=1.5
GLOORBOT_NAV_DELAY_MAX=3.9
GLOORBOT_BLOCK_IMAGES=1
GLOORBOT_BLOCK_FONTS=1
GLOORBOT_BLOCK_MEDIA=1
GLOORBOT_BLOCK_ANALYTICS=1
GLOORBOT_VIEWPORT_WIDTH=1280
GLOORBOT_VIEWPORT_HEIGHT=720
```
