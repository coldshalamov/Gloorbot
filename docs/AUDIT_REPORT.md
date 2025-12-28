# Gloorbot Distributed Scraper - Audit Report

**Date:** 2025-12-27
**Auditor:** Claude Code

---

## Executive Summary

The distributed scraper architecture is **well-designed and mostly complete**. The coordinator properly handles task leasing, deal aggregation, and live updates. The worker correctly integrates with the proven PARALLEL/scraper.py logic including the critical pickup filter.

**Critical issues found:** 2
**Minor issues found:** 4
**Fixes applied:** 2

---

## Repository Structure

```
apps/
├── coordinator/           # Render-hosted FastAPI service
│   ├── coordinator_app/   # Python package
│   │   ├── web.py         # API endpoints + dashboard
│   │   ├── models.py      # SQLAlchemy models (Client, Task, Deal)
│   │   ├── schemas.py     # Pydantic request/response schemas
│   │   ├── seed.py        # Task seeding from urls.txt
│   │   └── db.py          # Database connection
│   ├── data/urls.txt      # WA/OR stores + 600+ category URLs
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # CSS + JS for dashboard
│   ├── Dockerfile         # Docker build for Render
│   └── requirements.txt
│
└── worker/                # Windows desktop application
    ├── src/gloorbot_worker/
    │   ├── __main__.py    # Entry point (GUI or slot-worker mode)
    │   ├── gui.py         # Tkinter GUI (Join/Kill buttons)
    │   ├── supervisor.py  # Auto-scaling slot manager
    │   ├── slot_worker.py # Scraping logic + deal filtering
    │   ├── api.py         # HTTP client for coordinator
    │   └── paths.py       # LocalAppData paths
    ├── installer/worker.iss  # Inno Setup script
    ├── build.ps1          # Local build script
    └── pyproject.toml

PARALLEL/                  # Proven scraping logic (reused by worker)
├── scraper.py             # warmup, store context, pickup filter, pagination
├── orchestrator.py        # (legacy - not used by distributed system)
└── worker.py              # (legacy - not used by distributed system)

.github/workflows/
└── worker-build.yml       # GitHub Actions: builds WorkerSetup.exe

render.yaml                # Render Blueprint for coordinator deployment
```

---

## Issues Found & Fixes Applied

### CRITICAL Issues

#### 1. ✅ FIXED: db_session() was not a proper context manager

**Location:** `apps/coordinator/coordinator_app/db.py:41-42`

**Problem:** The function returned a raw Session without cleanup, risking connection leaks.

**Fix Applied:**
```python
@contextmanager
def db_session() -> Iterator[Session]:
    """Context manager for database sessions with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

#### 2. ✅ FIXED: Missing price validation in deal filtering

**Location:** `apps/worker/src/gloorbot_worker/slot_worker.py:80-90`

**Problem:** If `price >= was_price` (no discount), `pct_off` could be negative or zero, potentially submitting invalid deals.

**Fix Applied:**
```python
# Ensure price is actually discounted (price < was_price)
if price_now >= was_price:
    return None
```

---

### Minor Issues (Not Fixed - Document Only)

#### 3. store_info lacks city/state in slot_worker

**Location:** `apps/worker/src/gloorbot_worker/slot_worker.py:194-200`

**Impact:** Low - the scraper.py only uses `name` and `store_id` from store_info. City/state are used for logging but empty strings work.

**Recommendation:** Parse city/state from store_name if needed for better logging.

#### 4. EventBus is single-subscriber

**Location:** `apps/coordinator/coordinator_app/web.py:40-53`

**Impact:** Low - If multiple browsers connect to SSE, only one gets events (queue is consumed).

**Recommendation:** For production scale, use Redis pub/sub or broadcast pattern.

#### 5. No retry on coordinator unreachable during lease_next

**Location:** `apps/worker/src/gloorbot_worker/slot_worker.py:164-168`

**Impact:** Medium - Worker already has 10-second sleep on exception, but could be more robust.

**Current behavior:** Catches exception, sleeps 10s, continues loop. This is acceptable.

#### 6. Hardcoded version "0.1.0" in worker

**Location:** `apps/worker/src/gloorbot_worker/api.py:31,44`

**Impact:** Low - Version tracking is nice-to-have, not critical.

**Recommendation:** Read from package metadata or env var.

---

## What Works Well

### Coordinator
- ✅ Proper lease-based task distribution (15 min leases)
- ✅ Least-recently-scraped ordering ensures fair coverage
- ✅ Idempotent deal upserts (store_id + product_url unique)
- ✅ SSE for live dashboard updates
- ✅ Persistent disk for SQLite on Render
- ✅ Seed tasks from urls.txt on startup (idempotent)
- ✅ Health check endpoint for Render

### Worker
- ✅ No Python required - PyInstaller bundles everything
- ✅ Installs to LocalAppData (no admin required)
- ✅ Persistent browser profiles per store
- ✅ Auto-scaling slots (70-90% CPU/RAM target)
- ✅ Reuses proven PARALLEL/scraper.py logic
- ✅ Proper pickup filter application
- ✅ Block detection + 5-minute cooldown
- ✅ Desktop shortcut created by installer

### Build Pipeline
- ✅ GitHub Actions builds on Windows
- ✅ Playwright Chromium bundled via `--add-data`
- ✅ Inno Setup creates single .exe installer
- ✅ Artifact uploaded for download

---

## Anti-Bot Mitigations Preserved

The worker correctly uses the PARALLEL/scraper.py behavior:

1. **Headful browser** - Not headless, harder to detect
2. **Persistent profiles** - Cookies/storage persist across sessions
3. **Warmup session** - Visits benign pages first
4. **Store context** - Sets store before category browsing
5. **Pickup filter** - JavaScript-based click with verification
6. **Human-like delays** - Random sleeps between actions
7. **Block cooldown** - 5 minute wait if blocked, then fresh browser

---

## Recommendations for Future

1. **Add integration test** - Script that simulates lease→complete cycle without Playwright
2. **Add Sentry/logging** - Better error visibility in production
3. **Consider PostgreSQL** - SQLite is fine for moderate scale, but Postgres better for high concurrency
4. **Rate limiting** - Add per-client rate limits to prevent abuse
5. **Worker version check** - Coordinator could reject outdated workers

---

## Files Changed

| File | Change |
|------|--------|
| `apps/coordinator/coordinator_app/db.py` | Made db_session() a proper context manager |
| `apps/worker/src/gloorbot_worker/slot_worker.py` | Added price validation (price < was_price) |
| `docs/DEPLOY_CHECKLIST.md` | Created deployment guide |
| `docs/AUDIT_REPORT.md` | This report |

---

## Conclusion

The distributed scraper is **ready for deployment**. The architecture is sound, the critical pickup filter logic is properly integrated, and the worker installer should work for non-technical users.

Next steps:
1. Push changes to GitHub
2. Deploy coordinator via Render Blueprint
3. Run GitHub Action to build WorkerSetup.exe
4. Create GitHub Release with installer
5. Set WORKER_DOWNLOAD_URL in Render
6. Distribute to volunteers
