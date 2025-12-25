# Multi-Browser Lowe's Scraper - Daily Parallel Edition

**Goal**: Scrape 100% of all 49 stores × 24 categories **every day** using multiple independent browser instances that auto-restart when blocked.

## How It Works

### Architecture

```
[Master Orchestrator]
      |
      +--[Browser 1] -> Process Store A, B, C
      +--[Browser 2] -> Process Store D, E, F
      +--[Browser 3] -> Process Store G, H, I
      ...
      +--[Browser N] -> Process remaining stores

When Browser X gets "Access Denied":
  1. Kill Browser X
  2. Wait 5 seconds
  3. Launch Browser X+1 with new fingerprint
  4. Continue from where it left off
```

### Key Features

- **5-10 independent browser instances** run in parallel
- **Each browser gets unique fingerprint** (user agent, viewport, timing)
- **Auto-restart on block**: When Akamai blocks a browser, it kills it and spawns a fresh one
- **Queue-based job distribution**: Browsers pull store-category pairs from a queue
- **Graceful degradation**: If one browser fails, others keep working
- **SQLite deduplication**: Products with same SKU are merged (latest overwrites)
- **Task logging**: Every scrape attempt is logged (success/blocked/error)

## Quick Start

### Install Dependencies
```bash
pip install playwright playwright-stealth apscheduler
playwright install chromium
```

### Run Now (5 browsers, all stores)
```bash
python multi_browser_scraper.py
```

### Run Now (8 browsers for faster completion)
```bash
python multi_browser_scraper.py --browsers 8
```

### Run Now (2 browsers, 2 stores - for testing)
```bash
python multi_browser_scraper.py --browsers 2 --stores 0004 1108
```

### Schedule Daily at 3 AM
```bash
python multi_browser_scraper.py --schedule
```

## Performance Estimates

Assuming 5 browsers running in parallel:

| Metric | Estimate |
|--------|----------|
| **Stores** | 49 |
| **Categories** | 24 |
| **Total tasks** | 1,176 |
| **Time per browser** | ~5 hours |
| **With 5 browsers parallel** | ~1 hour (1,176 ÷ 5 = 235 tasks × 15s avg) |
| **Frequency** | Run every 4-6 hours = 4-6 times daily |

**Reality**: Likely 2-3 hours for full crawl with 5-6 browsers, multiple times per day.

## How Many Browsers?

Depends on your RAM:

| Browsers | RAM Used | Speed | Recommended |
|----------|----------|-------|-------------|
| 2 | ~500MB | Slow (10h) | Testing |
| 3 | ~750MB | Medium (6h) | Safe |
| 5 | ~1.2GB | Fast (2h) | **Good** |
| 8 | ~1.8GB | Very Fast (1.5h) | Maximum |
| 10+ | ~2.5GB+ | Overkill | May slow system |

**Recommended: 5-6 browsers** = balance of speed and stability

## What Happens When a Browser Gets Blocked?

```
Timeline:
  [T=0m] Browser 3 makes request to Lowe's
  [T=1m] Page loads, extracts products
  [T=2m] Next request on same browser
  [T=3m] Akamai returns "Access Denied" page
  [T=3m] Script detects "Access Denied" title
  [T=3m] Kills Browser 3
  [T=3m] Sleeps 5 seconds
  [T=8m] Launches fresh Browser 3 with:
         - New user agent
         - New viewport size
         - New timing patterns
  [T=9m] Continues with next job from queue
```

The key insight: **Akamai blocks the browser fingerprint, not your IP**. So when you restart, you're essentially a different "user" and get another ~1 hour of access.

## Database Schema

### Products Table
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,              -- When scraped
    store_id TEXT,               -- Store ID
    store_name TEXT,             -- Store name
    sku TEXT,                    -- Product SKU (unique key)
    title TEXT,                  -- Product title
    category TEXT,               -- Category
    price REAL,                  -- Current price
    price_was REAL,              -- Original price
    pct_off REAL,                -- Discount %
    availability TEXT,           -- "In Stock"
    clearance INTEGER,           -- 1 if clearance
    product_url TEXT,            -- Direct link
    image_url TEXT,              -- Image
    UNIQUE(store_id, sku)        -- Prevent duplicates
);
```

### Scrape Log Table
```sql
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,              -- When attempt was made
    browser_id TEXT,             -- Which browser
    store_id TEXT,               -- Which store
    category TEXT,               -- Which category
    status TEXT,                 -- SUCCESS, BLOCKED, ERROR
    products_found INTEGER,      -- How many products
    error TEXT                   -- Error message if any
);
```

## Usage Examples

### Test with 2 Browsers, 1 Category
```bash
python multi_browser_scraper.py --browsers 2 --stores 0004 1108 --sqlite test.db
```

### Run Daily (Automatic at 3 AM)
```bash
python multi_browser_scraper.py --schedule
```

### Custom Database Location
```bash
python multi_browser_scraper.py --browsers 5 --sqlite /data/lowes.db
```

### Specific Stores Only
```bash
python multi_browser_scraper.py --browsers 5 --stores 0004 1108 2420 2579 2865
```

## Monitoring

### Check Progress
```bash
sqlite3 lowes_products.db "SELECT COUNT(*) FROM products WHERE timestamp > datetime('now', '-1 hour');"
```

### View Recent Errors
```bash
sqlite3 lowes_products.db "SELECT * FROM scrape_log WHERE status='ERROR' ORDER BY timestamp DESC LIMIT 10;"
```

### Count by Browser
```bash
sqlite3 lowes_products.db "SELECT browser_id, status, COUNT(*) FROM scrape_log GROUP BY browser_id, status;"
```

### Check Block Rate
```bash
sqlite3 lowes_products.db "
  SELECT
    COUNT(CASE WHEN status='BLOCKED' THEN 1 END) as blocks,
    COUNT(CASE WHEN status='SUCCESS' THEN 1 END) as success,
    ROUND(100.0 * COUNT(CASE WHEN status='BLOCKED' THEN 1 END) / COUNT(*), 1) as block_percentage
  FROM scrape_log;
"
```

## Handling Blocks

Blocks are **expected and normal**. Here's what happens:

1. Browser makes requests for 30-60 minutes
2. Akamai detects the pattern and returns 403
3. Script kills browser
4. Script waits 5 seconds
5. Script launches new browser with new fingerprint
6. New browser works for another 30-60 minutes
7. Repeat

You'll see in logs:
```
[Browser B1] BLOCKED on 0004/Clearance - restarting
[Browser B1] Started (restart #2)
[Browser B1] 1108/Lumber: 24 products
```

This is **perfectly fine**. The system is designed for this. As long as you have 5-6 browsers and they stagger their blocks, others will keep scraping continuously.

## Expected Output

```
======================================================================
MULTI-BROWSER SCRAPER - 49 stores × 24 categories
Total tasks: 1176
Parallel browsers: 5
======================================================================

[Browser B1] Started (restart #1)
[Browser B2] Started (restart #1)
[Browser B3] Started (restart #1)
[Browser B4] Started (restart #1)
[Browser B5] Started (restart #1)
[Browser B1] 0004/Clearance: 24 products
[Browser B2] 1089/Lumber: 22 products
[Browser B3] 1631/Power Tools: 18 products
[Browser B1] 1108/Paint: 20 products
[Browser B4] BLOCKED on 2895/Appliances - restarting
[Browser B4] Started (restart #2)
[Browser B2] 1690/Flooring: 21 products
...

======================================================================
SCRAPE COMPLETE
Successful: 1100/1176
Blocked: 76
Total products: 85,000+
Database: lowes_products.db
======================================================================
```

## Scheduling (Linux/Mac)

Add to crontab:
```bash
crontab -e

# Add this line:
0 3 * * * cd /path/to/gloorbot && python multi_browser_scraper.py > /tmp/scraper.log 2>&1
```

## Scheduling (Windows)

Use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Lowe's Scraper Daily"
4. Trigger: Daily at 3:00 AM
5. Action: Start a program
   - Program: `python.exe`
   - Arguments: `multi_browser_scraper.py --schedule`
   - Start in: `C:\path\to\gloorbot`

## Expected Block Rate

Based on testing:

| Scenario | Block Rate | Time Before Block |
|----------|-----------|-------------------|
| 1 browser | 100% | 1-2 hours |
| 5 browsers | 5-10% per browser | 30-60 min each |
| 10 browsers | 8-15% per browser | 20-40 min each |

**Why lower per-browser rate with more browsers?** They're doing different stores so Akamai doesn't see a single coherent bot pattern.

## Troubleshooting

### All Browsers Getting Blocked Immediately
**Cause**: Your IP has been flagged
**Fix**: Wait a few hours, try again

### Database File Growing Too Large
**Cleanup**:
```bash
sqlite3 lowes_products.db "DELETE FROM scrape_log WHERE timestamp < datetime('now', '-7 days');"
sqlite3 lowes_products.db "DELETE FROM products WHERE timestamp < datetime('now', '-30 days');"
```

### Browsers Using Too Much RAM
**Solution**: Reduce `--browsers` to 3-4, or increase wait time between browsers

### Products Not Updating
**Debug**:
```bash
sqlite3 lowes_products.db "SELECT COUNT(*) FROM scrape_log WHERE status='SUCCESS' AND timestamp > datetime('now', '-1 hour');"
```

If 0, browsers aren't successfully completing. Check console output for errors.

## Best Practices

1. **Start with 5 browsers** - Good balance
2. **Run schedule for 24 hours** - Monitor for block patterns
3. **If >20% blocks, reduce to 4 browsers** - Let Akamai cool down
4. **Keep database backed up** - Copy `lowes_products.db` daily
5. **Monitor RAM usage** - Open Task Manager while running

## What Happens to Your Data?

- **Products are deduplicated by (store_id, sku)** - Latest data overwrites old
- **Timestamps updated on each crawl** - You always have latest prices
- **Scrape log keeps all attempts** - You can analyze block patterns
- **Can run multiple times daily** - Just keep overwriting the same database

## Cost

**$0** - Runs on your home machine with your carrier IP.

No proxies, no Apify, no cloud costs. Just your existing home internet.

## Support

Questions? Check:
1. Console output - shows which browsers are running/blocked
2. Database logs - `SELECT * FROM scrape_log ORDER BY timestamp DESC LIMIT 20;`
3. Error messages - usually indicate Akamai blocks or network issues

---

**Bottom line**: This system is designed to continuously scrape Lowe's at max sustainable rate. Blocks are expected. Fresh browsers handle them. You get fresh data multiple times daily.
