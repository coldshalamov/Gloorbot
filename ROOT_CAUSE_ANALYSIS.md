# Root Cause Analysis: Browser "Crash" Issue

## What You Saw
- 20+ Chrome processes running
- System freezing/crashing
- Workers stalling after ~1000 products

## What I Initially Thought (WRONG)
"Chrome is spawning too many subprocesses and needs to restart every 25 categories"

## What Was ACTUALLY Happening

### The Architecture
Your setup uses a **supervisor pattern**:

```
intelligent_supervisor.py
├── Worker 0 (subprocess) → run_single_store.py → main.py → Chrome browser
├── Worker 1 (subprocess) → run_single_store.py → main.py → Chrome browser
└── Worker 2 (subprocess) → run_single_store.py → main.py → Chrome browser
```

**Each Chrome instance has ~8-10 normal subprocesses:**
- Main browser process
- GPU process
- Network service
- Renderer process
- Audio service
- Utility processes
- etc.

So 2-3 workers = 20-30 Chrome processes = **COMPLETELY NORMAL**

### The REAL Problem

1. **Workers were hanging** due to missing timeouts on Playwright operations
2. **When a worker hung**, the supervisor detected it died and restarted it
3. **The hung Chrome instance wasn't being killed properly** before restart
4. **Over multiple restart cycles**, orphaned Chrome processes accumulated
5. **Eventually you had**:
   - Active workers with their Chrome instances (normal)
   - + Zombie Chrome instances from previous crashes (the problem)
   - + Hung Chrome instances that never responded to termination (the real problem)

### What Actually Needed Fixing

NOT "restart Chrome every 25 categories" (that's a hack that costs money on Apify)

BUT:
1. ✅ **Add timeouts to ALL Playwright operations** so workers don't hang forever
2. ✅ **Proper exception handling** so timeouts propagate correctly
3. ✅ **Ensure browser cleanup** when worker exits
4. ⚠️ **Supervisor needs to kill zombie Chrome processes** when restarting workers

## The Fixes Applied

### 1. Comprehensive Timeouts (CRITICAL)
Every Playwright operation now has a timeout:
- `page.goto()`: 60s max
- `page.title()`: 10s max
- `page.locator().all()`: 15s max
- Individual card extraction: 5s max per card
- Overall page scrape: 120s max

**Result**: Workers will NEVER hang indefinitely. If Lowe's blocks or page hangs, the timeout fires and worker moves to next page/category.

### 2. Scrape ALL Pages (Not Limited)
Changed from arbitrary page limits to `while True` loop that stops when:
- No products found (end of category)
- Partial page detected (< 12 products)
- Timeout occurs

**Result**: Complete product coverage per category.

### 3. Better Error Handling
Each category wrapped in try/except that logs error and continues.

**Result**: One failed category doesn't crash entire store scrape.

## What Still Needs Fixing

### Supervisor-Level Cleanup

The supervisor (intelligent_supervisor.py) needs to:

1. **Kill ALL Chrome processes** when stopping a worker:
```python
async def stop(self):
    if self.process:
        # Get all child processes (including Chrome)
        try:
            parent = psutil.Process(self.pid)
            children = parent.children(recursive=True)

            # Kill children first (Chrome processes)
            for child in children:
                try:
                    child.kill()
                except:
                    pass

            # Then kill main worker process
            self.process.terminate()
            self.process.wait(timeout=10)
        except:
            # Force kill everything
            self.process.kill()
```

2. **Check for orphaned Chrome before starting new worker**:
```python
async def start(self):
    # Kill any existing Chrome for this profile
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'chrome' in proc.name().lower():
                cmdline = ' '.join(proc.cmdline())
                if f'store-{self.store_info["store_id"]}' in cmdline:
                    proc.kill()
        except:
            pass

    # Then start worker...
```

## Cost Analysis: Browser Restart Hack vs Proper Timeouts

### Browser Restart Every 25 Categories (BAD):
- Per store: 515 categories / 25 = **21 browser restarts**
- Per restart: ~30 seconds (close + relaunch + warmup + set store)
- **Total overhead: 10.5 minutes per store of pure restart time**
- **Apify cost**: Charged for all restart time

### Proper Timeouts (GOOD):
- **Zero restart overhead**
- Browser runs continuously until store complete
- Only "cost" is failed pages that timeout (which were going to fail anyway)
- **Apify cost**: Only charged for actual scraping time

## Conclusion

The crashes weren't because Chrome needs periodic restarts. They were because:

1. **Missing timeouts** → workers hung forever
2. **Hung workers** → supervisor restarted them
3. **Incomplete cleanup** → old Chrome processes accumulated
4. **Accumulated processes** → system resource exhaustion → crash

The timeouts fix prevents hangs. The supervisor cleanup (not yet implemented) prevents accumulation.

**No browser restarts needed. This is how normal scrapers work.**
