# PARALLEL Lowe's Scraper

Self-contained, local scraper for Lowe's product data with intelligent blocking detection.

## What it does
- Scrapes product listings from all Lowe's stores in WA and OR
- 49 stores × 605 categories = comprehensive coverage
- Runs 5 Chrome browsers in parallel for speed
- Saves progress after each category (fully resumable)
- Detects blocking and waits 5 minutes before retry

## Requirements
- Python 3.9+
- Chrome browser installed
- Playwright (`pip install playwright && playwright install chromium`)
- psutil (`pip install psutil`)

## No proxies needed!
This runs locally on YOUR internet connection. The scraper uses human-like
mouse movements and timing to avoid detection. When blocked, it automatically
cools down for 5 minutes before resuming.

## How to run

**Windows:** Double-click `start.bat`

**Command line:**
```
python orchestrator.py --state WA,OR --max-workers 5
```

## Files
- `orchestrator.py` - Manages multiple worker processes with blocking detection
- `worker.py` - Wrapper for individual store scraping with checkpoint tracking
- `scraper.py` - Core browser automation logic with timeouts
- `urls.txt` - Store and category URLs (605 categories, 49 stores)
- `start.bat` - Easy launcher

## Output
- `output/` - JSONL files with product data (one per store)
- `logs/` - Worker logs for debugging
- `checkpoints/` - Progress files (for resuming if interrupted)
- `status/` - Worker status files (blocking detection)

## Configuration
Edit `start.bat` or run orchestrator.py directly:
- `--state WA,OR` - Which states to scrape (comma-separated)
- `--max-workers 5` - How many Chrome browsers to run

## If you get blocked
The scraper automatically handles blocking:
1. Detects "Access Denied" / "Robot" pages
2. Waits 5 minutes (cooldown period)
3. Resumes from last checkpoint

Manual options if blocking persists:
1. Reduce workers: `--max-workers 3`
2. Wait 15-30 minutes for IP to cool down
3. Check your network (VPN/proxy might help)

## Reliability Features
- **Checkpoints**: Every category completion saves progress
- **Status Files**: Workers communicate blocking status to orchestrator
- **Cooldown**: 5-minute wait after blocking before retry
- **Timeouts**: All Playwright operations have explicit timeouts
- **Human Behavior**: Mouse movement and scrolling patterns

## Tuning (in scraper.py)
- Wait times between pages: lines ~97, ~107, ~115, ~164, ~178
- Currently set ~50% slower than default for better anti-block
