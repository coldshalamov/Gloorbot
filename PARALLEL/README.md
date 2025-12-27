# PARALLEL Lowe's Scraper

This is a self-contained, local scraper for Lowe's product data.

## What it does
- Scrapes product listings from all Lowe's stores in WA and OR
- 49 stores × 716 categories = comprehensive coverage
- Runs 5 Chrome browsers in parallel for speed
- Saves progress after each category (resumable)

## Requirements
- Python 3.9+
- Chrome browser installed
- Playwright (`pip install playwright && playwright install chromium`)

## No proxies needed!
This runs locally on YOUR internet connection. The scraper uses human-like
mouse movements and timing to avoid detection. It was running successfully
on your mobile hotspot with occasional blocks that auto-recover.

## How to run

**Windows:** Double-click `start.bat`

**Command line:**
```
python orchestrator.py --state WA,OR --max-workers 5
```

## Files
- `orchestrator.py` - Manages multiple worker processes
- `worker.py` - Wrapper for individual store scraping
- `scraper.py` - Core browser automation logic
- `urls.txt` - Store and category URLs (716 categories, 49 stores)
- `start.bat` - Easy launcher

## Output
- `output/` - JSONL files with product data (one per store)
- `logs/` - Worker logs for debugging
- `checkpoints/` - Progress files (for resuming if interrupted)

## Configuration
Edit `start.bat` or run orchestrator.py directly:
- `--state WA,OR` - Which states to scrape (comma-separated)
- `--max-workers 5` - How many Chrome browsers to run

## If you get blocked
1. Reduce workers: `--max-workers 3`
2. Wait 10-15 minutes (IP cools down)
3. The scraper auto-restarts blocked workers

## Tuning (in scraper.py)
- Wait times between pages: lines ~97, ~107, ~115, ~164, ~178
- Currently set ~50% slower than default for better anti-block
