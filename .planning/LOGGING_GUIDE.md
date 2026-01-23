# Gloorbot Diagnostics & Logging Guide

## Overview

Instead of guessing why workers crash or tasks aren't being delegated properly, you can now see exactly what's happening through structured JSON logging visible on Render in real-time.

## What Gets Logged

### Browser Crashes
- **Event**: `worker_browser_crash`
- **Data**: slot_id, store_id, store_name, category_url, error, page_title, page_url, browser_state
- **Use**: Understand why browsers keep crashing (Akamai blocks, grid layout issues, memory, etc.)

### Task Delegation
- **Event**: `task_delegation`
- **Data**: slot_id, task_id, store_id, store_name, category_url, status (assigned/started/completed/failed), duration_seconds, products_found
- **Use**: See which tasks are being assigned to which workers and how long they take

### Grid Validation Failures
- **Event**: `grid_validation_failure`
- **Data**: page_num, store_id, store_name, category_url, page_url, reason
- **Use**: Identify which URLs have unexpected layouts or are redirecting to /c/ pages

### Redirects
- **Event**: `redirect_detected`
- **Data**: store_id, store_name, requested_url, landed_url, redirect_type
- **Use**: Find which URLs are causing redirects (redirect from /pl/ to /c/, etc.)

### Coordinator Dispatch
- **Event**: `coordinator_dispatch`
- **Data**: num_workers, num_available_tasks, num_tasks_leased, store_distribution
- **Use**: See how tasks are being distributed across workers

### Worker Heartbeat
- **Event**: `worker_heartbeat`
- **Data**: slot_id, client_id, tasks_completed, tasks_active, browser_alive, memory_mb
- **Use**: Monitor worker health and memory usage

## Accessing Logs

### Option 1: Via Render Dashboard (Easiest)
Logs are written to `/var/logs/gloorbot-structured.jsonl` which is **persistent on Render** and visible in the logs tab.

### Option 2: Via API Endpoints

The coordinator exposes structured logs through API endpoints:

**Get all logs (last 100 entries):**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/logs
```

**Get only browser crashes (last 50):**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/crashes
```

**Get task delegation logs (last 100):**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/task-delegation
```

**Get grid validation failures (last 50):**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/grid-failures
```

### Option 3: Local Testing
When running locally, logs are written to `./logs/gloorbot-structured.jsonl`

## Example: Debugging the "Kendall Lowes Crash Whack-a-Mole"

**Before:** Multiple browsers crashing, no visibility into why
**After:** Follow these steps:

1. **Check browser crashes:**
   ```bash
   curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/crashes | jq '.[] | {timestamp, store_name, category_url, error}'
   ```

2. **Look for patterns:**
   - Are all crashes happening at same store? (Geolocation issue)
   - Same category across stores? (URL problem)
   - Same error message? (Specific issue)

3. **Check grid validation failures:**
   ```bash
   curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/grid-failures | jq '.[] | {timestamp, store_name, page_url, reason}'
   ```

4. **Check task delegation:**
   ```bash
   curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/task-delegation | jq '.[] | {timestamp, task_id, store_name, status, duration_seconds, error}'
   ```

This tells you:
- Which URLs cause grid validation failures (unexpected layout)
- Which tasks are failing and why
- How long tasks take to complete or fail
- Which stores are problematic

## Log Format

All logs are structured JSON with this base format:

```json
{
  "timestamp": "2026-01-23T15:30:45.123456",
  "event": "event_name",
  "level": "INFO|WARNING|ERROR",
  ...event-specific fields...
}
```

Example worker_browser_crash:
```json
{
  "timestamp": "2026-01-23T15:30:45.123456",
  "event": "worker_browser_crash",
  "level": "ERROR",
  "slot_id": 1,
  "store_id": "2573",
  "store_name": "Kendall, FL",
  "category_url": "https://www.lowes.com/pl/...",
  "error": "Navigation timeout after 60s",
  "page_title": "Access Denied",
  "page_url": "https://www.lowes.com/blocked",
  "browser_state": "crashed"
}
```

## What This Solves

### Problem: "Browsers keep crashing like whack-a-mole"
**Solution:** Check crash logs to see:
- Is it Akamai blocks? (Access Denied page title)
- Is it memory? (Check memory_mb in heartbeat)
- Is it specific URLs? (Check which category_urls are crashing)
- Is it specific stores? (Check which store_ids are failing)

### Problem: "Workers aren't being delegated tasks properly"
**Solution:** Check task_delegation logs to see:
- Are tasks being assigned? (assigned status)
- Are they being picked up? (started status)
- Are they completing? (completed status)
- Which tasks fail? (failed status with error)
- Are specific stores getting tasks? (store_distribution in coordinator_dispatch)

### Problem: "Something changed and it broke on Jan 23"
**Solution:** Look at logs before/after that time:
```bash
# Get logs from that time period
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/logs?limit=500
```

## Parsing Tips

### jq filters for common queries

**Find all errors:**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/logs | \
  jq '.[] | select(.level == "ERROR")'
```

**Find crashes in specific store:**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/crashes | \
  jq '.[] | select(.store_id == "2573")'
```

**Find tasks taking > 10 minutes:**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/task-delegation | \
  jq '.[] | select(.duration_seconds > 600)'
```

**Count crashes by store:**
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/diagnostics/crashes | \
  jq 'group_by(.store_name) | map({store: .[0].store_name, count: length})'
```

## Real-Time Monitoring

The logs are continuously written as events happen. You can:

1. **Watch Render dashboard logs tab** - See raw logs in real-time
2. **Poll API endpoints** - Refresh every 10-30 seconds
3. **grep local logs** - If testing locally:
   ```bash
   tail -f logs/gloorbot-structured.jsonl | grep worker_browser_crash
   ```

## Debugging Workflow

1. **Something is broken**
2. **Check crashes** - Are browsers crashing?
3. **Check grid failures** - Are URLs causing validation issues?
4. **Check task delegation** - Are tasks being completed?
5. **Check coordinator dispatch** - Are tasks being distributed?
6. **Find patterns** - Which stores/URLs/errors are common?
7. **Fix root cause** - Not the symptom

Example: Multiple crashes at Kendall (store 2573):
- Check crash logs → see "grid_validation_failure" reason
- Check grid failures → see all are missing product links
- Check category URLs being sent to Kendall → find problematic URL pattern
- Fix the URL or add redirect detection
- Monitor next day → confirm crashes stop

## Integration Points

Logs are automatically written by:

1. **Coordinator** (`apps/coordinator/coordinator_app/web.py`)
   - Task assignment (lease_next endpoint)
   - Task completion (lease_complete endpoint)
   - Task failures (lease_fail endpoint)

2. **Worker** (PARALLEL/scraper.py)
   - Grid validation failures
   - Redirect detection
   - Browser crashes (caught by eventlog already)

3. **Structured Logs Module** (new)
   - Centralized logging to `/var/logs/gloorbot-structured.jsonl`
   - Easy filtering and parsing

## Performance Notes

- Logs are appended to JSONL file (efficient, one entry per line)
- No performance impact on scraping/coordination
- On Render, logs persist across restarts
- API endpoints read last N lines efficiently
- For high-volume queries, use Render's log storage directly

## Future Enhancements

Possible improvements:
- Time-range filtering in API endpoints
- Aggregation endpoints (crashes per store, tasks per store, etc.)
- Prometheus metrics export
- Alert endpoints (e.g., "10 crashes in last 5 minutes")
- Search by URL, store, error message
