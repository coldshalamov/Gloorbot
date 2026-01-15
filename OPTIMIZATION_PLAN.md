# Optimization Implementation Plan

## 1. Files to Delete (Housekeeping)
These files are confirmed redundant and safe to remove:
- `local_scraper.py` (Legacy, unused)
- `intelligent_scraper.py` (Deprecated)
- `simple_scraper.py` (Test script)
- `diagnostic_scraper.py` (Likely unused)
- `working_scraper.py` (Old backup)

## 2. Code Changes

### A. Add Resource Blocking to `apps/worker/src/gloorbot_worker/slot_worker.py`

**Add these imports:**
```python
import re
from playwright.async_api import Route
```

**Add this function (e.g., before `_run_slot`):**
```python
# Resource blocking configuration
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
BLOCKED_URL_PATTERNS = [
    r"google-analytics\.com", r"googletagmanager\.com", r"facebook\.net",
    r"doubleclick\.net", r"analytics", r"tracking", r"beacon", r"pixel",
    r"ads\.", r"ad\.", r"adservice", r"pagead",
    r"youtube\.com", r"vimeo\.com", r"brightcove",
    r"twitter\.com/widgets", r"pinterest\.com", r"linkedin\.com",
    r"hotjar\.com", r"clarity\.ms", r"newrelic\.com", r"sentry\.io",
    r"segment\.com", r"optimizely\.com", r"fullstory\.com", r"heap\.io",
    r"amplitude\.com", r"mixpanel\.com", r"intercom\.io", r"drift\.com",
    r"zendesk\.com", r"livechat\.com", r"tawk\.to",
    r"\.woff2?(\?|$)", r"\.ttf(\?|$)", r"\.eot(\?|$)",
]
NEVER_BLOCK_PATTERNS = [
    r"/_sec/", r"/akam/", r"akamai", r"lowes\.com",
    r"cloudfront", r"/pl/", r"/pd/", r"/c/",
]

async def setup_request_interception(page: Page) -> None:
    """Block heavy resources to speed up execution."""
    async def handle_route(route: Route):
        request = route.request
        url = request.url.lower()
        resource_type = request.resource_type

        # 1. Allow essential patterns
        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.continue_()
                return

        # 2. Block heavy resource types
        if resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return

        # 3. Block tracking/ad patterns
        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", handle_route)
```

**Call it in `_run_slot`:**
```python
# ... inside ensuring browser/page ...
page = await context.new_page()
await setup_request_interception(page)  # <--- ADD THIS LINE
# ... then continue with warmup ...
```

### B. Optimize Delays in `PARALLEL/scraper.py`
Reduce the hardcoded sleeps in `scrape_category_page`.

**Search & Replace:**
- `await asyncio.sleep(1.5 + random.random() * 2.4)` -> `await asyncio.sleep(0.5 + random.random() * 0.5)`
- `await asyncio.sleep(2.0 + random.random() * 2.55)` -> `await asyncio.sleep(0.5 + random.random() * 0.5)`
- `await asyncio.sleep(1.5 + random.random() * 1.75)` -> `await asyncio.sleep(0.5 + random.random() * 0.5)`
- `await asyncio.sleep(6.0 + random.random() * 4.0)` -> `await asyncio.sleep(2.0 + random.random() * 1.0)`

## 3. Configuration Results
- **Browser**: Stick with `headless=False` (required for Akamai).
- **Channel**: Use `channel="chrome"` (`GLOORBOT_PREFER_CHROME=1` is already default).
- **Parallelism**: With resource blocking enabled, you can likely increase the number of worker slots per machine by 2-3x due to reduced CPU/RAM usage.
