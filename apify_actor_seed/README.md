# Lowe's Pickup Today Scraper - Apify Actor

Scrape **"Pickup Today"** inventory across 50+ Lowe's stores in Washington and Oregon using Apify's massive parallelization architecture.

## Features

- **Massive Parallelization**: Uses Apify's Request Queue to process 27,000+ URLs across 100+ parallel instances
- **Akamai Bypass**: Headful Playwright with residential proxies and session locking
- **Race Condition Fixed**: Proper pickup filter application with verification
- **Auto-scaling**: Apify automatically scales workers based on queue size
- **Incremental Results**: Products pushed to Dataset as they're scraped

## Performance

| Metric | Value |
|--------|-------|
| Stores | 50+ (WA/OR) |
| Categories | 500+ |
| Max Pages/Category | 20 (480 items) |
| Target Runtime | 5-15 minutes |
| Parallelization | 100+ workers |

## Input Schema

```json
{
    "store_ids": [],           // Empty = all 50+ WA/OR stores
    "categories": [],          // Empty = all 500+ categories from LowesMap.txt
    "max_pages_per_category": 20,
    "use_stealth": true,
    "proxy_country": "US"
}
```

## Output Schema

```json
{
    "store_id": "1234",
    "store_name": "Lowe's Seattle",
    "sku": "1000123456",
    "title": "2x4x8 Lumber",
    "category": "Building Materials",
    "price": 5.98,
    "price_was": 6.98,
    "pct_off": 0.14,
    "availability": "In Stock",
    "clearance": false,
    "product_url": "https://www.lowes.com/pd/...",
    "image_url": "https://mobileimages.lowes.com/...",
    "timestamp": "2025-12-08T19:00:00Z"
}
```

## Architecture

### Request Queue Pattern

```
1. Enqueue ALL URLs upfront (stores × categories × pages)
   └── 50 stores × 500 categories × 20 pages = 500,000 URLs

2. Apify auto-scales workers to process queue
   └── 100+ parallel browser instances

3. Each worker locks proxy session to store_id
   └── Prevents Akamai "Access Denied" errors

4. Results pushed incrementally to Dataset
   └── Real-time visibility into progress
```

### Anti-Bot Strategy

1. **Residential Proxies** with session locking per store
2. **Headful Playwright** (Akamai blocks headless)
3. **playwright-stealth** for fingerprint evasion
4. **Human-like delays** between actions

### Pickup Filter Fix

The original code had a race condition where it clicked the filter before the page loaded. Fixed by:

1. `wait_for_load_state('networkidle')` before clicking
2. Verify filter applied via:
   - URL parameter check
   - aria-checked/pressed state
   - Product count change
3. Multiple retry attempts with verification

## Local Testing (FREE - No Apify Costs!)

### Quick Setup
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### Test 1: Single Page (Simplest)
```bash
# Scrape ONE page, see if it works
python test_single_page.py

# With custom URL
python test_single_page.py --url "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"
```

### Test 2: Pickup Filter Validation
```bash
# Test JUST the pickup filter fix across 3 URLs
python test_pickup_filter.py
```

### Test 3: Full Local Run (Mock Apify)
```bash
# Quick test: 1 store, 1 category, 1 page
python test_local.py

# Full test: 3 stores, 5 categories, 2 pages each
python test_local.py --full

# Custom test
python test_local.py --store 0061 --pages 2
python test_local.py --stores "0061,1089,0252" --pages 3
```

### Test Options
| Flag | Description |
|------|-------------|
| `--headless` | Run headless (faster but may get blocked) |
| `--no-proxy` | Direct connection (no proxy) |
| `--store ID` | Test specific store |
| `--pages N` | Max pages per category |
| `--full` | Run comprehensive test |

### Expected Output
```
[INFO] Processing: Store 0061 | Lumber | Page 1
  Pickup filter: Applied
  Found 24 products
[DATA] Saved 24 items (total: 24)
```

Results saved to `test_output.json`

## Deploy to Apify

```bash
# Push to Apify platform
apify push
```

## Files Structure

```
├── .actor/
│   ├── actor.json          # Actor configuration
│   ├── input_schema.json   # Input parameters
│   └── dataset_schema.json # Output schema
├── src/
│   ├── main.py            # Main Actor entry point
│   └── __init__.py
├── catalog/
│   ├── building_materials.lowes.yml
│   └── wa_or_stores.yml
├── input/
│   └── LowesMap.txt       # Store & category URLs
├── Dockerfile
├── requirements.txt
└── README.md
```

## Critical Notes

1. **MUST use headless=False** - Akamai aggressively blocks headless browsers
2. **MUST lock proxy session to store_id** - Changing IPs mid-store triggers blocks
3. **MUST apply pickup filter on EVERY page** - Pagination URLs don't preserve filter
4. **Check for crashes AFTER page.goto()** - Chromium's "Aw, Snap!" happens post-navigation

## License

Proprietary - For authorized use only.
