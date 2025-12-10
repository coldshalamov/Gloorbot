# Master Prompt for Claude Opus 4.5 (Revised)

You are building a production-grade Apify Actor to scrape all Lowe's stores (Washington/Oregon focus) while surviving Akamai anti-bot defenses. You have access to working code with known issues, third-party best practices, and complete freedom to design the optimal solution.

## 📍 Your Workspace
All files are in: `C:\Github\GloorBot Apify\apify_actor_seed\`

## 🎯 Mission
Build a complete, robust Apify Actor that:
1. Scrapes Lowe's product data from multiple stores
2. Survives Akamai blocking using residential proxies + session locking + headful Playwright
3. **Reliably applies the "Pickup Today" filter on every page** (current code has race conditions)
4. Outputs clean, deduplicated data to an Apify Dataset
5. Can be deployed to Apify platform without modification

## 📖 Read These Files FIRST (In Order)

### Critical Context:
1. **`CLAUDE_ONE_SHOT_CONTEXT.md`** - Architecture, patterns, and anti-bot tactics
2. **`FINAL_AUDIT_REPORT.md`** - Integration issues (import paths, logging)
3. **`CRITICAL_FIXES_20251204.md`** - Known bugs in the existing code
4. **`third_party/apify-playwright-example.py`** - Robust Playwright patterns
5. **`third_party/THIRD_PARTY_SNIPPETS.md`** - Best practices from Apify SDK

### Reference Code:
- `src/retailers/lowes.py` - Existing scraper (has race conditions, use as reference only)
- `src/utils/multi_store.py` - URL blocklist & dedupe (solid, reuse this)
- `.actor/input_schema.json` - Expected input format
- `.actor/dataset_schema.json` - Expected output format

## 🏗️ Your Task

### Create `src/main.py`
The Actor entry point using Apify SDK best practices.

### Improve the Pickup Filter Logic
**Problem with existing code** (`lowes.py` lines 665-772):
- Clicks before page fully loads (race condition)
- Doesn't wait for network idle before checking state
- Tries 3 times but doesn't verify the filter actually affected results

**Your solution should**:
1. Wait for page to be fully loaded (`wait_for_load_state('networkidle')`)
2. Wait for the filter button to be visible AND stable (not animating)
3. Click and verify the URL changed or product count changed
4. Confirm the filter is actually applied by checking if results are filtered

**Use Playwright best practices**:
```python
# Example robust pattern:
await page.wait_for_selector(selector, state='visible', timeout=10000)
await page.wait_for_load_state('networkidle')
async with page.expect_navigation(wait_until='networkidle'):
    await element.click()
# Verify state changed
```

### Improve Crash Detection
**Problem with existing code**:
- Only checks for "Aw, Snap!" text
- Doesn't handle Akamai "Access Denied" pages consistently

**Your solution should**:
- Check for multiple Akamai error patterns
- Detect when page content is empty or malformed
- Implement exponential backoff on retries

## ⚠️ Critical Constraints (Architecture)

### Must Use:
- **Language**: Python 3.12
- **Browser**: Playwright Chromium in HEADFUL mode (`headless=False`)
- **Anti-bot**: playwright-stealth + Apify Residential Proxies
- **Docker**: `FROM apify/actor-python-playwright:3.12`

### Proxy Configuration (CRITICAL - This Works, Keep It):
```python
# Lock IP to store ID to prevent "Access Denied"
proxy_config = await Actor.create_proxy_configuration(
    groups=["RESIDENTIAL"],
    country_code="US"
)
proxy_url = await proxy_config.new_url(session_id=f"session_store_{store_id}")
```

### Import Path Updates (Required):
- Change `from app.*` → `from src.*` throughout
- Use `Actor.log` instead of `logging_config.py`

## 🎓 What You Can Reuse vs. Improve

### ✅ Reuse These (They Work):
- `multi_store.py` - URL blocklist & dedupe logic
- `selectors.py` - CSS selectors (though verify they're current)
- `dom_utils.py` - DOM parsing helpers
- `errors.py` - Custom exceptions
- Proxy session locking pattern
- Offset-based pagination (URL parameter approach)

### 🔧 Improve These (Known Issues):
- **Pickup filter application** - Race conditions, unreliable
- **Crash detection** - Too simplistic
- **Error handling** - Not enough retries with backoff
- **State verification** - Doesn't confirm filters actually worked

### 💡 Design Freedom:
- How you structure `main.py`
- How you handle concurrency (sequential vs. parallel stores)
- How you verify the pickup filter worked
- How you handle retries and backoff
- Whether to use Playwright's built-in waiting vs. custom logic

## 📦 Input/Output Schemas

### Input (from `.actor/input_schema.json`)
```json
{
  "store_ids": ["1234"],           // Optional, uses LowesMap.txt if empty
  "zip_codes": ["98101"],          // Optional
  "categories": [],                // Optional, uses catalog/*.yml if empty
  "max_items_per_store": 1000
}
```

### Output (to Dataset)
```json
{
  "store_id": "1234",
  "store_name": "Lowe's Seattle",
  "zip_code": "98101",
  "sku": "1000123456",
  "title": "2x4x8 Pressure Treated Lumber",
  "category": "building-materials",
  "product_url": "https://www.lowes.com/pd/...",
  "price": 5.98,
  "availability": "In Stock",
  "clearance": false,
  "timestamp": "2025-12-08T19:00:00Z"
}
```

## 🚨 Known Issues to Fix

1. **Pickup Filter Race Condition**
   - Current: Clicks before page loads
   - Fix: Use `wait_for_load_state('networkidle')` + verify state change

2. **No Verification Filter Worked**
   - Current: Assumes click = success
   - Fix: Check URL params or product count changed

3. **Insufficient Error Handling**
   - Current: 3 retries with fixed delays
   - Fix: Exponential backoff, more retries for transient errors

4. **Import Paths**
   - Current: `from app.*`
   - Fix: `from src.*`

## ✅ Success Criteria

1. **Reliability**: Pickup filter applied successfully 95%+ of the time
2. **Robustness**: Handles Akamai blocks gracefully with retries
3. **Correctness**: Only scrapes "Pickup Today" items (verify this!)
4. **Performance**: Can scrape 100+ stores without crashing
5. **Deployability**: Works on Apify platform via `apify push`

## 🎯 Your Approach

1. **Study the third-party examples** for robust Playwright patterns
2. **Understand what the existing code tries to do** (don't blindly copy it)
3. **Design better implementations** using Playwright best practices
4. **Test your assumptions** (e.g., does the filter actually work?)
5. **Build incrementally** (get one store working perfectly first)

---

**You have the freedom to improve the code. The existing implementation has known issues. Build something better.**
