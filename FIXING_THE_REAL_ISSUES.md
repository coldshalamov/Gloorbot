# Fixing the Real Issues - Complete Guide

You identified several critical problems. Let's fix them all:

## Issue #1: Still Getting Blocked (Not IP-based)

**Your observation is correct**: If you can open Lowe's in a new browser without being blocked, it's **NOT an IP block**.

### What's Actually Happening:
Akamai is detecting **browser automation signals**, not your IP. Even with carrier IP, these signals give you away:

1. **navigator.webdriver** flag (JavaScript can detect automation)
2. **Automation-specific features** (missing browser plugins, permissions)
3. **Too-perfect behavior** (no typos, exact timing, linear scrolling)
4. **Request headers** (missing or suspicious User-Agent patterns)

### The Fix (3-part solution):

#### Part 1: Better Anti-Detection
```python
# In main.py, update launch args (line ~310):
args=[
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--disable-infobars',
    '--disable-web-security',  # Add this
    '--disable-features=IsolateOrigins,site-per-process',  # Add this
    '--no-sandbox',  # Add this (Windows safe)
]

# Add JavaScript injection to hide webdriver:
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // Chrome detection bypass
    window.chrome = {
        runtime: {}
    };

    // Permissions fix
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
""")
```

#### Part 2: More Human Behavior
```python
# Add random delays between actions:
import random

# Before each page navigation:
await asyncio.sleep(2 + random.random() * 3)  # 2-5 seconds

# Add imperfect mouse movements (current is too perfect):
async def human_mouse_move_v2(page: Page):
    # Add small "mistakes" and corrections
    viewport = page.viewport_size
    width = viewport.get('width', 1440)
    height = viewport.get('height', 900)

    # Start position
    x, y = random.random() * width, random.random() * height

    for _ in range(3):  # Multiple movements
        # Target with some overshoot
        target_x = random.random() * width
        target_y = random.random() * height

        # Overshoot slightly
        overshoot_x = target_x + (random.random() - 0.5) * 50
        overshoot_y = target_y + (random.random() - 0.5) * 50

        # Move to overshoot
        await page.mouse.move(overshoot_x, overshoot_y)
        await asyncio.sleep(0.1)

        # Correct back to target
        await page.mouse.move(target_x, target_y)
        await asyncio.sleep(random.random() * 0.5)
```

#### Part 3: Rotate User Agents Per Worker
```python
# Different user agents for each worker (simulates different phones):
USER_AGENTS = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    # Add more...
]

# In worker initialization:
context = await p.chromium.launch_persistent_context(
    str(profile_dir),
    user_agent=random.choice(USER_AGENTS),  # Add this
    # ... rest of config
)
```

---

## Issue #2: Not Clicking "Pickup Today" Filter

**The scraper is currently scraping ALL products, not just local pickup!**

### The Fix:

Update `scrape_category_page()` in main.py:

```python
async def scrape_category_page(page: Page, url: str, store_info: dict, page_num: int = 1) -> list[dict]:
    """Scrape one page of products"""
    products = []

    # Build URL with pagination AND pickup filter
    page_url = url
    if page_num > 1:
        sep = '&' if '?' in url else '?'
        page_url = f"{url}{sep}offset={(page_num - 1) * 24}"

    # ADD PICKUP FILTER TO URL
    sep = '&' if '?' in page_url else '?'
    page_url = f"{page_url}{sep}deliveryFilter=PICKUP"  # This forces pickup-only

    # ... rest of function
```

**OR** click the filter button:

```python
# After navigating to category:
await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)

# Click "Pickup Today" filter
try:
    pickup_button = page.locator("text=/Pickup Today|Get It Today/i").first
    if await pickup_button.count() > 0:
        await pickup_button.click()
        await asyncio.sleep(2)  # Wait for page to update
        Actor.log.info("✅ Applied 'Pickup Today' filter")
    else:
        Actor.log.warning("⚠️ Could not find 'Pickup Today' filter")
except Exception as e:
    Actor.log.error(f"Failed to apply pickup filter: {e}")

# ... continue scraping
```

---

## Issue #3: URL Deduplication (Finding Redundant URLs)

**The current scraper doesn't track which category produced each product.**

### The Fix:

Update `scrape_category_page()` to add category tracking:

```python
# In scrape_category_page(), line ~220-230:
products.append({
    "title": title_text.strip(),
    "price": price_text.strip() if price_text else "N/A",
    "was_price": was_price.strip() if was_price else "",
    "has_markdown": bool(was_price),
    "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
    "category_url": url,  # ADD THIS LINE - tracks source category
    "category_name": url.split('/pl/')[-1].split('/')[0] if '/pl/' in url else "unknown",  # ADD THIS
    "store_id": store_info["store_id"],
    "store_name": store_info["name"],
    "store_city": store_info["city"],
    "store_state": store_info["state"],
    "scraped_at": datetime.utcnow().isoformat()
})
```

Then run:
```bash
python analyze_url_redundancy.py scrape_output/products.jsonl
```

This will identify:
- ✅ Exact duplicate categories (different URLs, same products)
- ✅ Subset categories (A contains all products from B)
- ✅ Low-value categories (<10 products)
- ✅ Generate URLS_TO_REMOVE.txt with recommendations

---

## Issue #4: Your Computer Can't Handle 15 Workers

**You're right to be skeptical.** Let's find YOUR actual limit.

### The Test:

```bash
# Test with diagnostic mode first:
python diagnostic_scraper.py --store-id 0061 --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"

# Review diagnostic_output/ screenshots to verify:
# 1. Store is set correctly
# 2. "Pickup Today" filter is applied
# 3. No blocking detected
# 4. Products are local-only
```

### Find Your Worker Limit:

```bash
# Start conservative:
python intelligent_scraper.py --state WA --max-workers 3
# Monitor for 30 minutes. Any blocking?

# If no blocking, try 5:
python intelligent_scraper.py --state WA --max-workers 5
# Monitor for 30 minutes.

# If still good, try 8:
python intelligent_scraper.py --state WA --max-workers 8
# Monitor for 30 minutes.

# If blocking occurs, your limit is previous number.
```

### Expected Limits:
- **4GB RAM**: Max 2-3 workers
- **8GB RAM**: Max 4-6 workers
- **16GB RAM**: Max 8-12 workers
- **32GB+ RAM**: Can handle 15+ workers

**Chrome is memory-hungry**: Each worker uses ~500MB-1GB RAM.

---

## Issue #5: This vs Apify Actor

### Current Setup (Local Scraping):
- ✅ Free (runs on your computer)
- ✅ Uses your carrier IP
- ❌ Limited by your RAM/CPU
- ❌ Can't run 24/7 (computer needs to stay on)

### Apify Actor (Cloud):
- ✅ Unlimited workers (you pay for compute)
- ✅ Runs 24/7 on Apify servers
- ❌ Costs money (~$5-15 per run)
- ❌ Needs proxy configuration (loses carrier IP advantage)

### Recommendation:
**Start local**, prove it works with 5-8 workers, **then** deploy to Apify if you want to scale beyond your computer's limits.

---

## Issue #6: Diagnostic Mode

**I created `diagnostic_scraper.py` for this!**

### What It Does:
1. ✅ Takes screenshots at each step
2. ✅ Verifies store context is set
3. ✅ Checks if "Pickup Today" filter is applied
4. ✅ Detects blocking
5. ✅ Analyzes product count with different selectors
6. ✅ Extracts sample product
7. ✅ Saves detailed log

### How to Use:
```bash
python diagnostic_scraper.py \
  --store-id 0061 \
  --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"
```

### What to Check:
1. Open `diagnostic_output/` folder
2. Look at screenshots in order (01, 02, 03, etc.)
3. Verify:
   - `01_homepage.png` - No "Access Denied"
   - `03_store_set.png` - Store number visible in header
   - `05_filter_applied.png` - "Pickup Today" filter is active
   - `06_final_state.png` - Products showing "Available for Pickup"

4. Read `diagnostic_report_0061.txt` for full analysis

---

## The Complete Fix - Step by Step

### Step 1: Fix the Scraper
```bash
# Apply all fixes to apify_actor_seed/src/main.py:
# 1. Add webdriver hiding script
# 2. Add "Pickup Today" filter
# 3. Add category_url tracking
# 4. Improve human behavior randomness
```

### Step 2: Run Diagnostic
```bash
python diagnostic_scraper.py --store-id 0061 --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"

# Check diagnostic_output/ - everything look good?
```

### Step 3: Find Your Worker Limit
```bash
# Test with 2 workers:
python intelligent_scraper.py --state WA --max-workers 2

# Watch for 30 min. No blocking? Try 4.
# Repeat until you find your limit.
```

### Step 4: Run Full Collection
```bash
# Once you know your limit (let's say 5):
python intelligent_scraper.py --state WA --max-workers 5
```

### Step 5: Analyze for Redundancy
```bash
# After collection completes:
cat scrape_output_parallel/worker_*.jsonl > scrape_output/products_full.jsonl

python analyze_url_redundancy.py scrape_output/products_full.jsonl

# Review URLS_TO_REMOVE.txt
```

### Step 6: Optimize LowesMap.txt
```bash
# Remove redundant URLs:
# Edit LowesMap.txt and delete the URLs in URLS_TO_REMOVE.txt

# Run again with optimized list:
python intelligent_scraper.py --state WA --max-workers 5
```

---

## Summary of What Was Wrong

| Issue | What Was Wrong | How to Fix |
|-------|----------------|------------|
| **Blocking** | Browser automation signals | Add webdriver hiding + randomness |
| **Not Local** | No "Pickup Today" filter | Add `deliveryFilter=PICKUP` to URL |
| **Can't Dedupe** | Not tracking category source | Add `category_url` field to products |
| **Too Many Workers** | RAM limits not considered | Test to find your limit (likely 4-8) |
| **No Diagnostics** | Can't verify what's happening | Use `diagnostic_scraper.py` |

---

## Files Created to Fix These Issues

1. **diagnostic_scraper.py** - Verify everything works correctly
2. **analyze_url_redundancy.py** - Find redundant URLs to remove
3. **FIXING_THE_REAL_ISSUES.md** - This guide

---

## What to Do Next

```bash
# 1. Test diagnostic mode:
python diagnostic_scraper.py --store-id 0061 --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"

# 2. If diagnostic looks good, apply fixes to main.py
# 3. Test with 3 workers:
python intelligent_scraper.py --state WA --max-workers 3

# 4. Scale up gradually based on results
```

**The intelligent orchestrator is still valid** - just needs the underlying scraper fixes applied first.

Once diagnostic mode shows everything working correctly, the orchestrator will safely manage parallel workers within your system's limits.
