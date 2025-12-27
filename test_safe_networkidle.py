"""
Test WITH safe networkidle handling (matches working Cheapskater version)
Key difference: wrap wait_for_load_state in try-except and continue on timeout
"""

import asyncio
from playwright.async_api import async_playwright

async def safe_wait_for_load(page, state):
    """Match Cheapskater's _safe_wait_for_load - silently continue on timeout"""
    try:
        await page.wait_for_load_state(state)
    except Exception:
        return

async def test():
    async with async_playwright() as p:
        # Apply stealth to Playwright instance BEFORE launch
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print("Launching Chromium...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        print("\n1. Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        print(f"   Title: {await page.title()}")

        print("\n2. Setting store context...")
        try:
            store_btn = await page.wait_for_selector('[data-testid*="store"]', timeout=5000)
            await store_btn.click()
            await asyncio.sleep(1)

            zip_input = await page.wait_for_selector('input[placeholder*="ZIP"]', timeout=5000)
            await zip_input.fill("98144")
            await asyncio.sleep(0.5)
            await zip_input.press("Enter")
            await asyncio.sleep(3)
            print("   Store context set")
        except Exception as e:
            print(f"   Warning: {e}")

        print("\n3. Navigating to Clearance with pickup filter params...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607?pickupType=pickupToday&availability=pickupToday&inStock=1&offset=0"
        print(f"   URL: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # CRITICAL: Use safe wait like Cheapskater does
        print("   Waiting for networkidle (with safe catch)...")
        await safe_wait_for_load(page, "networkidle")
        await asyncio.sleep(2)

        title = await page.title()
        print(f"\n4. Page title: {title}")

        if "Access Denied" in title:
            print("   [BLOCKED] Got Access Denied")
        else:
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   [SUCCESS] Found {len(product_cards)} product cards")

            if len(product_cards) > 0:
                # Extract first product to verify
                first_card = product_cards[0]
                try:
                    title_el = await first_card.query_selector("a[href*='/pd/']")
                    title_text = await title_el.inner_text() if title_el else "Unknown"
                    print(f"   First product: {title_text[:60]}")
                except Exception as e:
                    print(f"   Could not extract product: {e}")

        await page.screenshot(path="test_safe_networkidle.png")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(test())
