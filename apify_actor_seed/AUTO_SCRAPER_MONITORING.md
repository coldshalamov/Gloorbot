# Auto-Scraper Monitoring Guide

## Quick Status Check

When you come back from your shower, check these files:

### 1. **auto_scraper_status.txt** (Updated every 30 seconds)
This is the easiest way to check status. Open this file and you'll see:
```
Auto-Scraper Status Report
Generated: 2025-12-05 11:30:45
======================================================================

Cycle: #2
Running Stores: 3
Completed This Cycle: 15/49
Ready to Launch: 20
In Retry Cooldown: 5
Max Retries Reached: 6

System Resources:
  CPU: 45.2%
  RAM: 62.1%

Recent Outcomes (last 10):
  0061: ✓ SUCCESS
  1089: ✗ FAILED
  2528: ✓ SUCCESS
  ...

Error Tracking:
  Consecutive Failures: 0
  1089: 2 failures, last: PAGE_CRASH
  2579: 1 failures, last: TIMEOUT
```

### 2. **Log Files** (In logs/ directory)
- `logs/parallel_gui_YYYYMMDD_HHMMSS.log` - Main auto-scraper log
- Look for these key indicators:

**Good Signs:**
```
✓ COMPLETED in 12.5 minutes
[0061] ✓ Page 1 found 24 products
[0061] Clicking pickup filter: 'Pickup Today'
STATUS: Cycle #2 | Running: 3 | Completed: 15/49
```

**Problem Signs:**
```
✗ FAILED after 5.2 minutes
⚠️  CRASH DETECTED - Browser/page crashed
⚠️  BLOCKED - Access denied detected
⚠️  PICKUP FILTER NOT FOUND - Recording ALL items!
⚠️  Page 3 is EMPTY - No products found!
⚠️  AKAMAI BLOCK DETECTED!
```

### 3. **Database** (orwa_lowes.sqlite)
Check if products are being saved:
```python
import sqlite3
conn = sqlite3.connect('orwa_lowes.sqlite')
cursor = conn.execute('SELECT COUNT(*) FROM observations')
print(f"Total products: {cursor.fetchone()[0]}")

# Recent products
cursor = conn.execute('SELECT store_id, title, price, ts FROM observations ORDER BY ts DESC LIMIT 10')
for row in cursor:
    print(row)
```

## What the Auto-Scraper Does

1. **Launches stores** one at a time (every 15 seconds)
2. **Monitors system resources** (stops launching if CPU > 80% or RAM > 85%)
3. **Handles all errors:**
   - Page crashes → Auto-reloads page
   - Browser crashes → Restarts browser (up to 3 times)
   - Akamai blocks → Increases delays, retries with backoff
   - Timeouts → Retries with longer timeout
   - Out of memory → Waits 30 sec, retries

4. **Smart retrying:**
   - Each store gets up to 3 retries
   - Exponential backoff (2min, 4min, 8min between retries)
   - Skips stores that max out retries until next cycle

5. **Cycles through all stores:**
   - When all 49 stores complete/max-retry → starts Cycle #2
   - Runs forever until you stop it

## Expected Behavior

**First 30 minutes:**
- Should see 10-15 stores complete
- Some stores may fail and retry
- CPU should be 40-80%
- RAM should be 50-85%

**After 2 hours:**
- Should complete first cycle (all 49 stores attempted)
- Start seeing "Cycle #2" in status
- Database should have 50,000+ products

**After overnight:**
- Multiple cycles completed
- Database should have 100,000-500,000+ products
- Some stores may be in "Max Retries Reached" (that's OK - they'll retry next cycle)

## Warning Signs

🚨 **Stop if you see:**
- RAM consistently > 95% (system will crash)
- All stores showing "✗ FAILED" (something is very wrong)
- "Consecutive Failures: 10+" (blocking or major issue)
- No status file updates for >5 minutes (crashed)

🟡 **Investigate if you see:**
- "Max Retries Reached" for >10 stores (may need parameter tuning)
- "⚠️  PICKUP FILTER NOT FOUND" for many stores (filter selectors may have changed)
- Multiple "⚠️  AKAMAI BLOCK DETECTED" (delays may need increase)

✅ **Good signs:**
- Mix of ✓ SUCCESS and occasional ✗ FAILED
- CPU 40-80%, RAM 50-85%
- "Running: 2-5" stores at a time
- Status file updating every 30 seconds

## Logs to Check

1. **auto_scraper_status.txt** - Quick overview (check first!)
2. **logs/parallel_gui_*.log** - Detailed logs (if problems)
3. **orwa_lowes.sqlite** - Verify data being saved

## Common Issues & Solutions

**Issue**: "This browser is already running"
**Cause**: Browser didn't clean up from previous crash
**Solution**: Kill all Chrome processes, delete `.playwright-parallel-profiles/`, restart

**Issue**: Pages keep crashing
**Cause**: Out of memory
**Solution**: Reduce MAX_CONCURRENT_STORES in auto_parallel_scraper.py (currently 8)

**Issue**: Getting blocked frequently
**Cause**: Too fast, Akamai detection
**Solution**: Increase delays in app/playwright_env.py

**Issue**: No products found for many stores
**Cause**: Pickup filter not being clicked
**Solution**: Check if Lowes changed their UI (selectors may need update)

## Quick Commands

**Stop auto-scraper:**
- Press Ctrl+C in the window

**Check status:**
- Open `auto_scraper_status.txt`

**Check database size:**
```bash
ls -lh orwa_lowes.sqlite
```

**Tail logs:**
```bash
tail -f logs/parallel_gui_*.log
```

**Count products:**
```bash
sqlite3 orwa_lowes.sqlite "SELECT COUNT(*) FROM observations"
```
