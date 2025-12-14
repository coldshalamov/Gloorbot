# Lowe's Pickup Today Inventory Scraper

Scrape **"Pickup Today"** inventory across **49 Lowe's stores** in Washington and Oregon. Find local markdowns, clearance items, and sales available for same-day pickup.

## Architecture: Sequential Context Rotation

**Why NOT Browser Pooling?**

| Approach | RAM Usage | Apify Cost |
|----------|-----------|------------|
| Browser Pooling (50 browsers) | 50x base | $400+/run |
| **Sequential Rotation (1 browser)** | 1x base | **~$25-30/run** |

This scraper uses **one browser with context rotation per store**, reducing costs by ~90% while maintaining session locking for Akamai evasion.

## Key Features

- **49 Stores**: All Lowe's in Washington (35) and Oregon (14)
- **24 Categories**: High-value departments (Clearance, Lumber, Tools, Appliances, etc.)
- **Smart Pagination**: Stops early when products run out (30-50% fewer requests)
- **Resource Blocking**: Blocks images, fonts, analytics (60-70% bandwidth savings)
- **Pickup Filter**: Physical click with verification (URL params don't work)
- **Akamai Evasion**: Residential proxies + session locking + stealth

## Cost Breakdown

| Component | Estimate |
|-----------|----------|
| Stores | 49 |
| Categories | 24 |
| Pages per category (avg) | ~10 |
| **Total requests** | ~11,760 |
| Bandwidth (w/ blocking) | ~2-3 GB |
| **Residential proxy cost** | ~$25-30 |
| **Compute cost** | ~$2-5 |
| **Total per run** | **~$27-35** |

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

### 4. Pickup Filter (Physical Click)
```python
# URL params like ?availability=pickup DON'T work
# Must physically click the filter element and verify
element = await page.query_selector('label:has-text("Get It Today")')
await element.click()
# Verify via aria-checked or URL change
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
