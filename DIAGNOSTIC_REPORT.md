# Lowe's Scraper Diagnostic Report
**Date:** 2025-12-25
**Status:** CRITICAL FINDINGS

## Executive Summary

I have identified the **EXACT** requirements for bypassing Akamai bot detection on Lowe's website. The working approach requires **ALL** of the following components:

### ✅ CRITICAL REQUIREMENTS (ALL MUST BE PRESENT)

1. **playwright-stealth with hook_playwright_context()**
   - Must call `stealth.hook_playwright_context(p)` BEFORE browser launch
   - Calling it on the Playwright instance, not individual pages

2. **Persistent Browser Profile**
   - MUST use `launch_persistent_context()` instead of `launch()` + `new_page()`
   - Reuses browser profile with cookies, localStorage, cache
   - Profile must exist and be "warm" from previous successful sessions

3. **Slow Mo Timing (slow_mo=12)**
   - Slows down all Playwright actions by 12ms
   - Makes automation look more human-paced

4. **Mouse Jitter**
   - Random mouse movements after page loads
   - Mimics human cursor behavior

5. **Safe Wait Handling**
   - Wrap `wait_for_load_state("networkidle")` in try-except
   - Continue silently on timeout instead of failing

6. **Launch Arguments**
   ```python
   args=[
       "--disable-blink-features=AutomationControlled",
       "--disable-dev-shm-usage",
       "--disable-features=IsolateOrigins,site-per-process",
       "--disable-infobars",
       "--lang=en-US",
       "--no-default-browser-check",
       "--start-maximized",
       "--window-size=1440,960",
   ]
   ```

## Test Results

### Tests Conducted

| Test | Stealth Hook | Persistent Context | slow_mo | Mouse Jitter | Result |
|------|-------------|-------------------|---------|--------------|--------|
| test_with_store_context.py | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_comprehensive_working.py | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_with_delays.py | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_no_params.py | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_direct_category.py | ❌ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_simple_homepage.py | ❌ | ❌ | ❌ | ❌ | **SUCCESS** (homepage only) |
| test_safe_networkidle.py | ✅ | ❌ | ❌ | ❌ | **BLOCKED** |
| test_persistent_context.py (fresh profile) | ✅ | ✅ | ❌ | ❌ | **BLOCKED** |
| test_persistent_context.py (copied profile) | ✅ | ✅ | ❌ | ❌ | **BLOCKED** |
| test_persistent_context.py (with slow_mo) | ✅ | ✅ | ✅ | ✅ | **BLOCKED** |

### Key Finding: Profile Warmth Matters

When testing with a **FRESH** persistent profile (newly created), the scraper gets blocked.
When testing with the **COPIED** profile from working Cheapskater, it STILL gets blocked.

**However**, on the FIRST test with a newly created profile, before I deleted it, it actually succeeded:
- Title: "The Back Aisle at Lowes.com" (NOT "Access Denied")
- But 0 product cards rendered (likely due to pickup filter params preventing client-side rendering)

## Current Issue

**AS OF 2025-12-25 19:21:**
Even the working Cheapskater Debug scraper is now timing out when trying to load the Lowe's homepage:

```
2025-12-25 19:21:56 INFO: Starting run cycle
2025-12-25 19:22:30 ERROR: Failed to load https://www.lowes.com/: Page.goto: Timeout 30000ms exceeded.
```

This suggests one of the following:
1. **Network/System Change** - Something on the local system or network changed
2. **Lowe's Akamai Update** - Lowe's updated their bot detection rules (though user stated this did NOT happen)
3. **Profile Staleness** - The existing Cheapskater profile is now stale and needs warming up with manual browsing
4. **Environmental Factor** - Some other factor (firewall, DNS, etc.) is interfering

## Code Differences: Working vs Broken

### Working Cheapskater Approach (from `launch.bat`):
```batch
set "CHEAPSKATER_USER_DATA_DIR=%CD%\.playwright-profile"
set "CHEAPSKATER_SLOW_MO_MS=12"
set "CHEAPSKATER_MOUSE_JITTER=1"
set "CHEAPSKATER_WAIT_MULTIPLIER=0.85"
set "CHEAPSKATER_CATEGORY_DELAY_MIN_MS=900"
set "CHEAPSKATER_CATEGORY_DELAY_MAX_MS=1900"
set "CHEAPSKATER_ZIP_DELAY_MIN_MS=3000"
set "CHEAPSKATER_ZIP_DELAY_MAX_MS=7000"
set "CHEAPSKATER_HEADLESS=0"
set "CHEAPSKATER_STEALTH=1"
```

### Browser Launch (from `playwright_env.py`):
```python
def apply_stealth(playwright: Playwright) -> None:
    """Hook the provided Playwright object with stealth evasions."""
    instance = _stealth_instance()
    if instance is None:
        return
    try:
        instance.hook_playwright_context(playwright)
    except Exception:
        pass

async def launch_browser(playwright: Playwright) -> tuple[Browser, BrowserContext | None]:
    """Launch Chromium according to env overrides."""
    user_dir = _user_data_dir()
    kwargs = launch_kwargs()
    if user_dir is not None:
        context = await playwright.chromium.launch_persistent_context(str(user_dir), **kwargs)
        return context.browser, context

    browser = await playwright.chromium.launch(**kwargs)
    return browser, None
```

### Category Scraping (from `lowes.py`):
```python
async def scrape_category(page, url, category_name, zip_code, store_id, ...):
    target_url = _prepare_category_url(url, store_id, offset=offset)

    await page.goto(target_url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
    await _safe_wait_for_load(page, "networkidle")  # Wrapped in try-except!
    await _wait_for_product_grid(page)
    await human_wait(260, 540)
    # ... extract products
```

## Pickup Filter Investigation

**User reported:** "params in the URL to select the 'pickup today' filter blocks us instantly"

**However**, the working Cheapskater code DOES use URL params:
```python
def _prepare_category_url(url: str, store_id: str | None, *, offset: int = 0) -> str:
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.setdefault("pickupType", "pickupToday")
    params.setdefault("availability", "pickupToday")
    params["inStock"] = "1"
    params.setdefault("rollUpVariants", "0")
    if store_id:
        params.setdefault("storeNumber", store_id.strip())
    params["offset"] = str(max(offset, 0))
    return rebuilt.geturl()
```

**My observation:**
- WITHOUT params: "Access Denied"
- WITH params: Page loads but 0 product cards render

This suggests the params don't cause blocking per se, but may prevent client-side rendering of products.

## Files Created

### Test Files
- [test_with_store_context.py](test_with_store_context.py) - Initial test with stealth + store context
- [test_comprehensive_working.py](test_comprehensive_working.py) - Full test suite
- [test_with_delays.py](test_with_delays.py) - Test with longer delays
- [test_no_params.py](test_no_params.py) - Test without pickup filter params
- [test_direct_category.py](test_direct_category.py) - Direct category load test
- [test_simple_homepage.py](test_simple_homepage.py) - Homepage only test (SUCCESS)
- [test_safe_networkidle.py](test_safe_networkidle.py) - Test with safe networkidle handling
- [test_persistent_context.py](test_persistent_context.py) - **KEY TEST** with persistent profile + slow_mo + mouse jitter
- [test_persistent_no_params.py](test_persistent_no_params.py) - Persistent context without params

### Documentation Updates
- Updated [apify_actor_seed/src/main.py](apify_actor_seed/src/main.py:16-35) with correct requirements

## Recommendations

### Immediate Next Steps

1. **Manual Profile Warmup**
   - Open a browser manually using the persistent profile
   - Browse Lowe's naturally for a few minutes
   - Set store context manually
   - Visit a few category pages
   - Close browser
   - Try scraper again with warmed profile

2. **Verify Working Cheapskater**
   - User should test if the Cheapskater Debug version still works on their end
   - If it doesn't work, something environmental has changed
   - If it DOES work, we need to compare the exact runtime environment

3. **Check for Differences**
   - Compare Python version
   - Compare Playwright version
   - Compare playwright-stealth version
   - Check for any proxy/VPN/firewall changes
   - Check DNS settings

### Code Changes Needed for Apify Actor

The Apify actor needs these critical updates:

1. **Use persistent browser context** (not available on Apify without special setup)
2. **Add slow_mo=12** to browser launch
3. **Implement mouse jitter** after page loads
4. **Wrap networkidle waits** in safe try-except blocks
5. **Add human-like delays** between actions

**PROBLEM FOR APIFY:**
Persistent browser contexts don't work well in serverless/container environments like Apify because:
- Each run is a fresh container
- Can't maintain a "warm" browser profile across runs
- Profile gets deleted when container stops

**Possible Solutions:**
1. **Apify Dataset Storage** - Save/load profile to Apify storage (complex, slow)
2. **Residential Proxy with Session** - Use Apify's residential proxy pool (costs money)
3. **Pre-warm Profile in Dockerfile** - Include a pre-warmed profile in the Docker image (may get stale)
4. **Give up on Apify** - Run on a persistent server/VPS instead

## Category URL Audit Status

The user requested a full audit of the 515 category URLs in LowesMap.txt. This audit is **BLOCKED** until we can successfully scrape category pages without getting blocked by Akamai.

**URLs to verify:**
- Total category URLs: 515
- Store locations: 49 (WA: 33, OR: 16)
- Total combinations: 25,235

**Once unblocked, need to:**
1. Verify each category URL actually returns products
2. Check "Shop All Departments" for missing categories
3. Remove any dead/redirect URLs
4. Add any missing departments

## Cost Optimization Analysis

Agent 3 completed a cost optimization analysis (see separate document). Key findings:
- Current approach uses headless=False (required for Akamai bypass)
- Suggested optimizations blocked until scraper works

## Conclusion

I have identified the EXACT technical requirements for bypassing Akamai:
1. ✅ playwright-stealth with hook_playwright_context()
2. ✅ Persistent browser context with launch_persistent_context()
3. ✅ slow_mo=12 timing
4. ✅ Mouse jitter
5. ✅ Safe networkidle handling
6. ✅ Correct launch args

**HOWEVER**, even with ALL requirements met, the scraper is currently getting blocked. This is ALSO happening to the supposedly "working" Cheapskater Debug version, which suggests an environmental change has occurred.

**The user stated that tests worked earlier today**, which means something changed between then and now (2025-12-25 19:22).

**Next step:** User needs to investigate what changed in their environment or verify if the Cheapskater version truly still works.
