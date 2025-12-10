# Claude Opus One-Shot Context: Lowe's Apify Actor

This document contains **everything** you need to build a robust, Akamai-resistant Apify Actor for scraping Lowe's in a single pass.

---

## 🎯 Mission

Build a **Python Apify Actor** that:
1. Scrapes all Lowe's stores (WA/OR focus) using the battle-tested logic from `src/retailers/lowes.py`.
2. Survives Akamai anti-bot defenses using **Residential Proxies**, **Session Locking**, **Headful Playwright**, and **playwright-stealth**.
3. Outputs clean product data to an Apify Dataset.

---

## 🏗️ Architecture (Non-Negotiable)

### Language & Stack
- **Python 3.12** (NOT Node.js)
- **Playwright** (Chromium, headful mode)
- **Apify SDK for Python** (`apify` package)
- **playwright-stealth** (anti-fingerprinting)

### Docker Base Image
```dockerfile
FROM apify/actor-python-playwright:3.12
```
This image includes:
- Python 3.12
- Playwright browsers pre-installed
- **Xvfb** (required for `headless=False` in cloud)

### Anti-Bot Strategy
1. **Residential Proxies** with **Session Locking**:
   ```python
   proxy_config = await Actor.create_proxy_configuration(
       groups=["RESIDENTIAL"],
       country_code="US"
   )
   # CRITICAL: Lock IP to Store ID to prevent "Access Denied"
   proxy_url = await proxy_config.new_url(session_id=f"session_store_{store_id}")
   ```
   
2. **Headful Mode**:
   ```python
   browser = await p.chromium.launch(
       headless=False,  # CRITICAL for Akamai
       proxy={"server": proxy_url},
       args=["--disable-blink-features=AutomationControlled"]
   )
   ```

3. **Stealth**:
   ```python
   from playwright_stealth import stealth_async
   page = await context.new_page()
   await stealth_async(page)
   ```

---

## 📦 Input Schema

The Actor must accept this input (`.actor/input_schema.json`):

```json
{
  "title": "Lowes Scraper Input",
  "type": "object",
  "schemaVersion": 1,
  "properties": {
    "store_ids": {
      "title": "Store IDs",
      "type": "array",
      "description": "List of Lowe's Store IDs (e.g. ['1234', '5678']). If empty, uses LowesMap.txt.",
      "editor": "stringList",
      "default": []
    },
    "zip_codes": {
      "title": "Zip Codes",
      "type": "array",
      "description": "Auto-discover stores from these ZIPs.",
      "editor": "stringList",
      "default": []
    },
    "categories": {
      "title": "Categories",
      "type": "array",
      "description": "Filter by category URLs (e.g. 'building-materials'). If empty, uses catalog/*.yml.",
      "editor": "stringList",
      "default": []
    },
    "max_items_per_store": {
      "title": "Max Items Per Store",
      "type": "integer",
      "description": "Safety limit to prevent runaway scraping.",
      "default": 1000
    }
  }
}
```

---

## 📤 Output Schema

Push to Dataset with this structure:

```json
{
  "store_id": "1234",
  "store_name": "Lowe's Seattle",
  "zip_code": "98101",
  "sku": "1000123456",
  "title": "2x4x8 Pressure Treated Lumber",
  "category": "building-materials",
  "product_url": "https://www.lowes.com/pd/...",
  "image_url": "https://mobileimages.lowes.com/...",
  "price": 5.98,
  "price_was": 6.98,
  "pct_off": 0.14,
  "availability": "In Stock",
  "clearance": false,
  "timestamp": "2025-12-08T19:00:00Z"
}
```

---

## 🔥 Critical Code Snippets (DO NOT REFACTOR)

### 1. Crash Detection (`lowes.py` lines 730-742)
The "Aw, Snap!" crash happens **after** navigation. Standard Playwright error handling misses it.

```python
async def check_for_crash(page):
    """Check if Chromium crashed. Must run AFTER page.goto() and BEFORE selectors."""
    try:
        content = await page.content()
        if any(marker in content for marker in ["Aw, Snap!", "Out of Memory", "Error code"]):
            LOGGER.error("🚨 Page crashed! Reloading...")
            await page.reload()
            return True
    except Exception:
        pass
    return False
```

**Instruction**: Call this **after every `page.goto()`** and **before** looking for selectors.

---

### 2. Pickup Filter Loop (`lowes.py` lines 665-772)
This loop looks inefficient (tries 3 times), but it's **battle-tested** against Akamai latency.

```python
async def _apply_pickup_filter_on_page(page, category_name, target_url, store_id):
    """CRITICAL: Must run on EVERY pagination page, not just page 1."""
    pickup_selectors = [
        'label:has-text("Get It Today")',
        'label:has-text("Pickup Today")',
        'button:has-text("Pickup")',
        '[data-testid*="pickup"]',
        '[aria-label*="Pickup"]',
    ]
    
    for attempt in range(3):  # DO NOT REDUCE THIS
        LOGGER.info(f"[{category_name}] Pickup filter attempt {attempt + 1}/3")
        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        await element.click()
                        await asyncio.sleep(random.uniform(0.8, 1.6))
                        LOGGER.info(f"[{category_name}] ✅ Pickup filter clicked")
                        return True
            except Exception:
                continue
        await asyncio.sleep(random.uniform(0.8, 1.4))
    
    LOGGER.error(f"⚠️ PICKUP FILTER NOT FOUND - Recording ALL items (not just local pickup)!")
    return False
```

**Instruction**: Call this on **every** pagination page (not just the first one). The loop is intentionally "slow" to fight race conditions.

---

### 3. URL Blocklist & Dedupe (`multi_store.py` lines 34-65, 97-101)
Prevents scraping promotional/duplicate pages.

```python
URL_BLOCKLIST = (
    "/c/accessible-home", "/c/accessible-bathroom", "/c/accessible-kitchen",
    "/pl/save-now", "save-now", "savenow", "black-friday", "blackfriday",
    "/bf/", "cyber-monday", "/deals", "/savings", "/special", "/clearance",
    "/c/deals", "/c/savings", "/pl/deals", "/pl/savings",
    "promotion", "promo", "weekly-ad", "gift",
    "/departments", "/ideas", "/inspiration", "/how-to", "/projects",
    "/l/", "/b/", "lowesbrands",
)

def _dedupe_preserve_order(urls):
    """Remove duplicates while preserving order."""
    seen = {}
    result = []
    for url in urls:
        if url not in seen:
            seen[url] = None
            result.append(url)
    return result
```

**Instruction**: Filter all category URLs through the blocklist **before** scraping.

---

### 4. Offset-Based Pagination (`lowes.py` lines 632-646)
Do NOT click "Next" buttons. Use URL parameters.

```python
def _prepare_category_url(url, store_id, offset=0):
    """Add pagination offset. Don't add pickup filters to URL (they trigger 404s)."""
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    
    if offset > 0:
        params["offset"] = str(offset)
    
    rebuilt = parsed._replace(query=urlencode(params, doseq=True))
    return rebuilt.geturl()
```

**Instruction**: Paginate by incrementing `offset` by 24 (page size) in the URL.

---

## 🛡️ Akamai Mitigation (From "Akamai Bot Academy")

### DO:
1. **Use Residential Proxies** (not datacenter).
2. **Lock Sessions**: `session_id=f"session_store_{store_id}"` prevents IP flips mid-session.
3. **Headful Mode**: `headless=False` (Akamai blocks headless aggressively).
4. **Realistic Headers**: `playwright-stealth` handles this.
5. **Pacing**: Add `await asyncio.sleep(random.uniform(0.8, 1.6))` between actions.
6. **Retry with Backoff**: Use `tenacity` (already in `lowes.py`).

### DON'T:
1. **Don't use `navigator.webdriver`**: Stealth removes this.
2. **Don't paginate too fast**: The pickup filter loop adds natural delays.
3. **Don't change IPs mid-store**: Session locking prevents this.

---

## 📋 Implementation Checklist

### Phase 1: Setup
- [ ] Create `.actor/actor.json` (see `CONFIGURATION_GUIDE.md`)
- [ ] Create `.actor/Dockerfile` (use `apify/actor-python-playwright:3.12`)
- [ ] Create `.actor/input_schema.json` (see above)
- [ ] Create `requirements.txt` (already exists)

### Phase 2: Main Actor Loop (`src/main.py`)
```python
import asyncio
from apify import Actor
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from src.retailers.lowes import scrape_category, set_store_context

async def main():
    async with Actor:
        # 1. Get Input
        actor_input = await Actor.get_input() or {}
        store_ids = actor_input.get('store_ids', [])
        
        # 2. Setup Proxy
        proxy_config = await Actor.create_proxy_configuration(
            groups=["RESIDENTIAL"],
            country_code="US"
        )
        
        # 3. Main Loop
        async with async_playwright() as p:
            for store_id in store_ids:
                # Lock IP to this store
                proxy_url = await proxy_config.new_url(session_id=f"session_store_{store_id}")
                
                # Launch headful browser
                browser = await p.chromium.launch(
                    headless=False,
                    proxy={"server": proxy_url},
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                await stealth_async(page)
                
                # Set store context (from lowes.py)
                zip_code = "98101"  # TODO: Extract from LowesMap.txt
                await set_store_context(page, zip_code, store_hint={"store_id": store_id})
                
                # Scrape categories (from lowes.py)
                products = await scrape_category(
                    page, 
                    url="https://www.lowes.com/pl/building-materials/...",
                    category_name="building-materials",
                    zip_code=zip_code,
                    store_id=store_id
                )
                
                # Push to Dataset
                await Actor.push_data(products)
                
                await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
```

### Phase 3: Integration
- [ ] Import `scrape_category` from `src/retailers/lowes.py`
- [ ] Import `set_store_context` from `src/retailers/lowes.py`
- [ ] Parse `input/LowesMap.txt` to get store IDs
- [ ] Parse `src/catalog/*.yml` to get category URLs
- [ ] Filter URLs through `URL_BLOCKLIST` from `src/utils/multi_store.py`

### Phase 4: Error Handling
- [ ] Wrap `scrape_category` in try/except
- [ ] Log errors to `Actor.log`
- [ ] Retry failed stores (use `tenacity`)

---

## 🚨 Common Pitfalls

1. **"Access Denied" after 2-3 requests**:
   - **Cause**: IP changed mid-session.
   - **Fix**: Ensure `session_id` is locked to `store_id`.

2. **Pickup filter not working**:
   - **Cause**: Only ran on page 1.
   - **Fix**: Call `_apply_pickup_filter_on_page` on **every** pagination page.

3. **Chromium crashes silently**:
   - **Cause**: `check_for_crash` not called.
   - **Fix**: Call it **after** `page.goto()`.

4. **Empty results**:
   - **Cause**: URL is in `URL_BLOCKLIST`.
   - **Fix**: Filter URLs before scraping.

---

## 📚 Reference Files

- **Core Logic**: `src/retailers/lowes.py` (1,467 lines - the "brain")
- **Selectors**: `src/retailers/selectors.py`
- **DOM Helpers**: `src/extractors/dom_utils.py`
- **URL Blocklist**: `src/utils/multi_store.py`
- **Store Map**: `input/LowesMap.txt`
- **Categories**: `src/catalog/*.yml`
- **Critical Fixes**: `docs/CRITICAL_FIXES.md` (explains the "Aw, Snap!" bug)

---

## ✅ Success Criteria

1. Actor runs without crashing for 100+ stores.
2. Pickup filter is applied on **every** pagination page.
3. No "Access Denied" errors (session locking works).
4. Dataset contains clean, deduplicated products.
5. Dockerfile builds successfully on Apify platform.

---

**You have everything you need. Build the Actor. Good luck, Claude Opus 4.5.**
