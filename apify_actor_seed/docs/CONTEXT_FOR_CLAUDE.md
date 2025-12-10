# Context for Claude Code - Building the Lowe's Apify Actor

This document contains Critical Instructions and Code Snippets to guide Claude when building the Python Apify Actor for Lowe's.

## 1. Architectural Mandates

*   **Language**: Python 3.12+ only. Do NOT use Node.js/TypeScript.
*   **Browser**: Playwright (Chromium).
*   **Head Mode**: **Headful (Non-Headless)**. `headless=False`.
    *   *Why?* Akamai aggressively blocks headless browsers.
    *   *How?* The Docker image `apify/actor-python-playwright:3.12` includes Xvfb.
*   **Proxies**: **Apify Residential Proxies** with **Session Locking**.
    *   *Why?* Changing IPs mid-session triggers "Access Denied". Lock IP to the Store ID.

## 2. Code Snippets (Copy These Patterns)

### A. Apify Actor Lifecycle (Python)
Use the `async with Actor:` context manager.

```python
import asyncio
from apify import Actor

async def main():
    async with Actor:
        # 1. Get Input
        actor_input = await Actor.get_input() or {}
        store_ids = actor_input.get('store_ids', [])
        
        # 2. Setup Proxy with Session Locking
        proxy_config = await Actor.create_proxy_configuration(
            groups=["RESIDENTIAL"], 
            country_code="US"
        )
        
        # 3. Main Loop
        for store_id in store_ids:
            # Lock IP to this specific store
            proxy_url = await proxy_config.new_url(session_id=f"session_store_{store_id}")
            
            # Launch Browser with this Proxy
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False, # CRITICAL: Headful mode
                    proxy={"server": proxy_url},
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                # ... perform scraping using lowes.py logic ...
                
        # 4. Push Results
        await Actor.push_data(results)

if __name__ == '__main__':
    asyncio.run(main())
```

### B. Playwright Stealth (Python)
We use `playwright-stealth` instead of manual injection.

```python
from playwright_stealth import stealth_async

# Inside your page creation logic:
context = await browser.new_context(...)
page = await context.new_page()
await stealth_async(page)
```

## 3. "Do Not Refactor" List

The following logic in `lowes.py` is battle-tested. **Do not optimize or rewrite it**:

1.  **Pickup Filter Loop (`_apply_pickup_filter_on_page`)**: 
    *   The loop that tries 3 times to click "Pickup" is NOT inefficient; it is necessary to beat Akamai latency. Keep it exact.
2.  **Crash Detection (`check_for_crash` / `CRITICAL_FIXES.md`)**:
    *   This function must run **AFTER** `page.goto()` returns and **BEFORE** you look for selectors. If it returns true, `page.reload()` immediately.
3.  **Pagination (`offset` parameter)**:
    *   Do not click "Next" buttons. Use the `offset` URL parameter logic in `_prepare_category_url`.

## 4. Input Configuration
The Actor `input` should accept:
*   `store_ids`: List[str] (Optional overrides)
*   `zip_codes`: List[str] (Optional overrides)
*   `categories`: List[str] (Filter by category)
*   `max_items`: int (Safety limit)

If `store_ids` is empty, the Actor should fallback to reading `input/LowesMap.txt`.
