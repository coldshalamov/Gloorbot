# Master Prompt for Claude Opus 4.5 - Lowe's Apify Actor

---

## 🎯 Your Mission

Build a **massively parallel Apify Actor** that scrapes **27,000+ product pages** across all Lowe's stores in Washington and Oregon—while surviving Akamai's anti-bot defenses.

**Business Goal**: Track "Pickup Today" inventory across 50+ stores to find clearance deals on building materials.

**Scale Challenge**: 50 stores × 540 pages/store = 27,000 pages. Must complete in **minutes, not hours**, using Apify's parallelization architecture.

---

## 📂 Your Workspace

**Location**: `C:\Github\GloorBot Apify\apify_actor_seed\`

### Quick Map:

```
apify_actor_seed/
├── src/                          # Working Python scraper (has bugs)
│   ├── retailers/lowes.py        # 1,467 lines - scraper logic
│   ├── utils/multi_store.py      # URL filtering & deduplication
│   └── utils/errors.py           # Custom exceptions
├── input/LowesMap.txt            # 50+ WA/OR store IDs
├── catalog/*.yml                 # Category definitions
├── third_party/                  # Apify SDK examples
│   ├── apify-playwright-example.py
│   └── THIRD_PARTY_SNIPPETS.md
└── .actor/                       # Platform config
    ├── actor.json
    └── input_schema.json
```

---

## 🏗️ Architecture: Apify's Massive Parallelization

### The Secret to Scraping 27k Pages Fast:

Apify Actors that scrape "thousands of pages in 10 seconds" use **Request Queue + Auto-scaling**:

1. **Request Queue**: Enqueue all 27,000 URLs upfront
2. **Auto-scaling**: Apify spawns 50-200 parallel browser instances
3. **Distributed Processing**: Each instance pulls URLs from the queue
4. **Session Management**: Each browser gets its own proxy session

### Implementation Pattern (Use This):

```python
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        # 1. Get input
        actor_input = await Actor.get_input() or {}
        store_ids = actor_input.get('store_ids', [])  # User can specify stores
        
        # 2. Open Request Queue (Apify's magic)
        request_queue = await Actor.open_request_queue()
        
        # 3. Enqueue ALL URLs upfront (27k URLs)
        for store_id in store_ids:
            for category_url in get_categories():  # From catalog/*.yml
                for page_num in range(20):  # 20 pages × 24 items = 480 items/category
                    url = build_url(category_url, store_id, offset=page_num*24)
                    await request_queue.add_request({
                        'url': url,
                        'userData': {
                            'store_id': store_id,
                            'category': category_url
                        }
                    })
        
        # 4. Setup proxy configuration (session per store)
        proxy_config = await Actor.create_proxy_configuration(
            groups=["RESIDENTIAL"],
            country_code="US"
        )
        
        # 5. Process queue with Playwright
        async with async_playwright() as p:
            while request := await request_queue.fetch_next_request():
                store_id = request['userData']['store_id']
                
                # Lock proxy session to store
                proxy_url = await proxy_config.new_url(session_id=f"store_{store_id}")
                
                browser = await p.chromium.launch(
                    headless=False,
                    proxy={"server": proxy_url}
                )
                
                page = await browser.new_page()
                
                # Scrape the page
                await page.goto(request['url'])
                products = await scrape_page(page)
                
                # Push results incrementally
                await Actor.push_data(products)
                
                # Mark request as handled
                await request_queue.mark_request_as_handled(request)
                
                await browser.close()
```

### Apify Auto-Scaling:

When you run this Actor on Apify platform with **auto-scaling enabled**:
- Apify detects the 27k-item queue
- Spawns 50-200 parallel instances automatically
- Each instance processes ~135-540 URLs
- **Total time**: 5-15 minutes for 27k pages

---

## 📥 Input Schema (User Controls)

```json
{
  "store_ids": ["1234", "5678"],  // OPTIONAL: Specific stores, or leave empty for all WA/OR
  "categories": [],               // OPTIONAL: Specific categories, or all from catalog/*.yml
  "max_pages_per_category": 20,  // Limit pagination (20 pages = 480 items)
  "max_concurrency": 100          // Max parallel browsers (Apify handles this)
}
```

**Key Feature**: User can scrape **all 50 stores** OR **just 2 stores** by changing `store_ids`.

---

## 🚀 Performance Architecture

### Target Performance:
- **27,000 pages** across 50 WA/OR stores
- **5-15 minute runtime** with Apify auto-scaling
- **100-200 concurrent browsers** (Apify manages this)

### How Apify Achieves This:

1. **Request Queue**: Distributed queue that multiple instances share
2. **Auto-scaling**: Apify spawns instances based on queue size
3. **Session Pooling**: Reuses proxy sessions intelligently
4. **Incremental Output**: `push_data()` streams results, no memory buildup

### Your Job:

1. **Enqueue all URLs upfront** (don't scrape sequentially)
2. **Use `request_queue.fetch_next_request()`** (Apify handles parallelization)
3. **Lock proxy sessions per store** (prevent "Access Denied")
4. **Push data incrementally** (don't accumulate in memory)

---

## ⚠️ Critical Anti-Bot Requirements

### Must Use:
- **Headful Playwright** (`headless=False`) - Akamai blocks headless
- **Residential Proxies** with session locking per store
- **playwright-stealth** for fingerprint masking
- **Pacing**: 0.5-1s delays between actions (Apify parallelism compensates)

### Proxy Session Locking (CRITICAL):

```python
# Lock IP to store_id to prevent mid-scrape "Access Denied"
proxy_url = await proxy_config.new_url(session_id=f"store_{store_id}")
```

**Why**: If you change IPs mid-store, Akamai detects it and blocks.

---

## 🔧 Known Issues to Fix

### 1. Pickup Filter Race Condition (Critical Bug)

**Current code** (`lowes.py` lines 665-772):
```python
# Clicks before page loads - FAILS 30% of the time
await element.click()
await asyncio.sleep(0.8)  # Hope it worked?
```

**Your fix**:
```python
# Wait for stability
await page.wait_for_load_state('networkidle')
await page.wait_for_selector(selector, state='visible')

# Click and verify
async with page.expect_navigation(wait_until='networkidle'):
    await element.click()

# Confirm filter applied (check URL params or product count)
if 'pickupToday' not in page.url:
    raise Exception("Pickup filter failed to apply")
```

### 2. Import Path Updates

Change `from app.*` → `from src.*` in all existing code.

### 3. Use Apify Logging

Replace `logging_config.py` with `Actor.log.info()`.

---

## 📚 Resource Guide

### Start Here:
1. **`CLAUDE_ONE_SHOT_CONTEXT.md`** - Architecture & anti-bot tactics
2. **`third_party/apify-playwright-example.py`** - Request Queue pattern

### If You Need Help:
- **Request Queue docs**: Search `third_party/` for "request_queue"
- **Proxy rotation**: See `third_party/proxy_rotation_example.py`
- **Akamai tactics**: Search `Akamai Bot Academy.txt` for "residential proxies"

### Reference Code (Use Wisely):
- **`src/retailers/lowes.py`** - Has pickup filter bug, but good for SKU extraction
- **`src/utils/multi_store.py`** - URL blocklist (reuse this)
- **`input/LowesMap.txt`** - Parse for store IDs

---

## 📤 Output Schema (Dataset)

```json
{
  "store_id": "1234",
  "store_name": "Lowe's Seattle",
  "sku": "1000123456",
  "title": "2x4x8 Pressure Treated Lumber",
  "price": 5.98,
  "availability": "In Stock",
  "clearance": false,
  "timestamp": "2025-12-08T19:00:00Z"
}
```

---

## ✅ Success Criteria

1. **Scale**: Scrape 27,000 pages in under 15 minutes with auto-scaling
2. **Flexibility**: User can specify store list OR scrape all WA/OR stores
3. **Reliability**: Pickup filter works 95%+ of the time
4. **Correctness**: Only returns "Pickup Today" items
5. **Deployability**: Works on Apify platform with auto-scaling

---

## 🎯 Implementation Checklist

- [ ] Use `Actor.open_request_queue()` for parallelization
- [ ] Enqueue all 27k URLs upfront (don't scrape sequentially)
- [ ] Lock proxy sessions per store (`session_id=f"store_{store_id}"`)
- [ ] Fix pickup filter race condition (wait for networkidle)
- [ ] Parse `input/LowesMap.txt` for store IDs
- [ ] Allow user to override store list via input
- [ ] Push data incrementally with `Actor.push_data()`
- [ ] Update imports from `app.*` to `src.*`
- [ ] Use `Actor.log` instead of `logging_config.py`

---

## 💡 Key Insight

**The existing code scrapes sequentially** (one store at a time). That's why it's slow.

**Your Actor must use Request Queue** to let Apify spawn 100+ parallel instances. That's how you scrape 27k pages in minutes.

---

**Build the Actor using Apify's Request Queue architecture. Let the platform handle parallelization. You focus on making each page scrape robust.**
