# Apify Actor Shape

## Input Suggestions
- categoryUrls or categories
- store ids or zip codes
- concurrency limits
- proxy settings and country
- headless toggle (default false)
- device pool or fingerprint constraints
- SessionPool tuning (maxUsageCount, maxErrorScore)
- wait multiplier or slow-mo
- userDataDir (optional)

## Behavior Must-Haves
- Headed Chromium.
- Stealth applied before fingerprint injection (if used).
- Fingerprint and device rotation.
- Human-like pacing and jitter.
- Block/crash detection and retry.
- Pagination and pickup filter per page.

## Output Schema
Push to dataset items with:
- store_id, store_name, zip
- sku, title, category
- product_url, image_url
- price, price_was, pct_off
- availability, clearance, timestamp
