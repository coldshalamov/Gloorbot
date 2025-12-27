# Lowe's Pickup Today Inventory Scraper

Scrape **"Pickup Today"** inventory across **49 Lowe's stores** in Washington and Oregon. Find local markdowns, clearance items, and sales available for same-day pickup.

## Architecture: 3x Parallel Execution (v2.1)

**Why NOT Browser Pooling?**

| Approach | RAM Usage | Duration | Cost |
|----------|-----------|----------|------|
| Browser Pooling (50 browsers) | 50x base | 5-8h | $400+/run |
| Sequential Rotation (1 browser) | 1x base | 16-34h | ~$25-30/run |
| **3x Parallel (v2.1)** | 3x base | **7-10h** | **~$35-48/run** |

This scraper uses **one browser with 3 concurrent contexts**, processing stores in batches of 3. This reduces completion time by ~60% while keeping costs reasonable.

### Parallel Architecture Details

- **Execution**: 49 stores divided into 17 batches of 3
- **Per Batch**: 3 stores scraped concurrently using `asyncio.gather()`
- **Session Locking**: Each store gets a locked proxy session for Akamai evasion
- **Memory**: 4GB minimum, 8GB maximum (3 contexts + overhead)
- **Batch Delay**: 2-4 seconds between batches to avoid rate limiting

## Key Features

- **49 Stores**: All Lowe's in Washington (35) and Oregon (14)
- **24 Categories**: High-value departments (Clearance, Lumber, Tools, Appliances, etc.)
- **3x Parallel Contexts**: Sub-12-hour completion (was 16-34h sequential)
- **Enhanced Pickup Filter**: Triple verification (element state + URL params + product count)
- **Smart Pagination**: Stops early when products run out (30-50% fewer requests)
- **Resource Blocking**: Blocks images, fonts, analytics (60-70% bandwidth savings)
- **Fail-Fast**: Skips entire category if pickup filter verification fails
- **Akamai Evasion**: Residential proxies + session locking + stealth

## Cost Breakdown (v2.1)

| Component | Estimate |
|-----------|----------|
| Stores | 49 |
| Categories | 24 |
| Pages per category (avg) | ~10 |
| **Total requests** | ~11,760 |
| Bandwidth (w/ blocking) | ~6-8 GB |
| **Residential proxy cost** | ~$27-36 |
| **Compute cost** | ~$8-12 |
| **Total per run** | **~$35-48** |

**Duration**: 7-10 hours (49 stores ÷ 3 parallel = 17 batches × 25-35 min/batch)

## Critical Requirements

1. **RESIDENTIAL PROXIES** - Datacenter/carrier IPs are blocked
2. **SESSION LOCKING** - Same IP per store session
3. **headless=False** - Akamai fingerprints and blocks headless
4. **Physical filter click** - URL parameters don't activate pickup filter

## Input Schema

```json
{
    "stores": [],                    // Empty = all 49 WA/OR stores
    "categories": [],                // Empty = all 24 categories
    "max_pages_per_category": 50     // 24 items/page = 1,200 max items
}
```

### Custom Store Selection
```json
{
    "stores": [
        {"store_id": "0004", "name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"},
        {"store_id": "1108", "name": "Tigard", "city": "Tigard", "state": "OR", "zip": "97223"}
    ]
}
```

### Custom Categories
```json
{
    "categories": [
        {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
        {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"}
    ]
}
```

## Output Schema

```json
{
    "store_id": "0004",
    "store_name": "Lowe's Rainier",
    "sku": "1000123456",
    "title": "DEWALT 20V MAX Cordless Drill",
    "category": "Power Tools",
    "price": 99.00,
    "price_was": 149.00,
    "pct_off": 0.3356,
    "availability": "In Stock",
    "clearance": true,
    "product_url": "https://www.lowes.com/pd/...",
    "image_url": "https://mobileimages.lowes.com/...",
    "timestamp": "2025-12-13T20:00:00Z"
}
```

## Deployment

### Deploy to Apify

```bash
# Install Apify CLI
npm install -g apify-cli

# Login
apify login

# Push to Apify
apify push
```

### Configure Proxy (REQUIRED)

In Apify Console:
1. Go to Actor settings
2. Under "Proxy configuration"
3. Select **RESIDENTIAL** proxy group
4. Set country to **US**

## Local Testing

**Note: Local testing will get blocked by Akamai without residential proxies. Use for code verification only.**

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run diagnostic (confirms Akamai blocking)
python test_akamai_diagnostic.py

# Test structure (will show "Access Denied" without proxy)
python test_production_scraper.py
```

## Files Structure

```
apify_actor_seed/
├── .actor/
│   ├── actor.json           # Actor configuration
│   ├── input_schema.json    # Input parameters
│   └── dataset_schema.json  # Output schema
├── src/
│   ├── main.py              # Production Actor (deploy this)
│   ├── lowes_production_scraper.py  # Standalone scraper
│   └── proxy_config.py      # Proxy provider configs
├── test_production_scraper.py   # Full test suite
├── test_akamai_diagnostic.py    # Block diagnostic
├── test_single_page.py          # Simple page test
├── Dockerfile
├── requirements.txt
└── README.md
```

## How It Works

### 1. Browser Launch
```python
browser = await pw.chromium.launch(
    headless=False,  # REQUIRED for Akamai
    args=["--disable-blink-features=AutomationControlled"]
)
```

### 2. Per-Store Context with Session-Locked Proxy
```python
proxy_url = await proxy_config.new_url(session_id=f"lowes_{store_id}")
context = await browser.new_context(proxy={"server": proxy_url})
```

### 3. Resource Blocking
```python
# Block: images, fonts, analytics, ads
# NEVER block: lowes.com, akamai scripts
```

### 4. Enhanced Pickup Filter (v2.1)
```python
# Triple verification ensures filter actually applied
async def apply_pickup_filter(page, category_name):
    # Get baseline before filter
    url_before = page.url
    count_before = await get_product_count()

    # Click filter element
    await element.click()
    await page.wait_for_load_state("networkidle")

    # VERIFICATION 1: Element state
    if aria-checked="true" or aria-pressed="true":
        return True

    # VERIFICATION 2: URL changed with filter params
    if "?refinement=pickup" in page.url:
        return True

    # VERIFICATION 3: Product count decreased
    count_after = await get_product_count()
    if 0 < count_after < count_before:
        return True

    # ALL verifications failed - SKIP CATEGORY
    return False
```

### 5. Smart Pagination
```python
# Stop early when:
# - Less than 6 products on page (category exhausted)
# - 2 consecutive empty pages
# - Block detected
```

## Troubleshooting

### "Access Denied" Error
- **Cause**: Akamai detected automation
- **Fix**: Ensure RESIDENTIAL proxies are configured with session locking

### Empty Results
- **Cause**: Pickup filter not applied
- **Fix**: Check filter selectors match current Lowe's UI

### High Costs
- **Cause**: Too many pages, images not blocked
- **Fix**: Reduce `max_pages_per_category`, verify resource blocking

## Performance Tuning

| Setting | Faster/Cheaper | More Data |
|---------|----------------|-----------|
| `max_pages_per_category` | 10 | 50 |
| Categories | Just Clearance | All 24 |
| Stores | 5 test stores | All 49 |

### Quick Test Run (~$2-3)
```json
{
    "stores": [
        {"store_id": "0004", "name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"}
    ],
    "categories": [
        {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}
    ],
    "max_pages_per_category": 5
}
```

## License

Proprietary - For authorized use only.
