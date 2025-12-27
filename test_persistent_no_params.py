"""
Test persistent context WITHOUT pickup filter params
Hypothesis: URL params trigger the blocking/empty page issue
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def safe_wait_for_load(page, state):
    """Match Cheapskater's _safe_wait_for_load - silently continue on timeout"""
    try:
        await page.wait_for_load_state(state)
    except Exception:
        return

async def test():
    # Use persistent profile directory
    profile_dir = Path("c:/Users/User/Documents/GitHub/Telomere/Gloorbot/.playwright-profile")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Apply stealth to Playwright instance BEFORE launch
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print(f"Launching Chromium with persistent context...")

        # Use launch_persistent_context like Cheapskater does
        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
                "--start-maximized",
                "--window-size=1440,960",
            ],
            viewport={"width": 1440, "height": 900}
        )

        page = context.pages[0] if context.pages else await context.new_page()

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

        print("\n3. Navigating to Clearance WITHOUT pickup filter params...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
        print(f"   URL: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Use safe wait like Cheapskater does
        print("   Waiting for networkidle (with safe catch)...")
        await safe_wait_for_load(page, "networkidle")
        await asyncio.sleep(3)

        try:
            title = await page.title()
            print(f"\n4. Page title: {title}")
        except Exception as e:
            print(f"\n4. Could not get title (page destroyed): {e}")
            title = "ERROR"

        if "Access Denied" in title:
            print("   [BLOCKED] Got Access Denied")
        else:
            # Wait for products to load
            print("   Waiting for products to load...")
            await asyncio.sleep(3)

            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   Found {len(product_cards)} product cards")

            if len(product_cards) > 0:
                print(f"   [SUCCESS] Page loaded with {len(product_cards)} products!")
                # Extract first 5 products
                for i, card in enumerate(product_cards[:5]):
                    try:
                        title_el = await card.query_selector("a[href*='/pd/']")
                        title_text = await title_el.inner_text() if title_el else "Unknown"

                        price_el = await card.query_selector("[data-testid*='price']")
                        price_text = await price_el.inner_text() if price_el else "$0"

                        print(f"   Product {i+1}: {title_text[:50]} - {price_text}")
                    except Exception as e:
                        print(f"   Could not extract product {i+1}: {e}")
            else:
                print("   [WARNING] No product cards found, checking for pickup filter button...")
                # Check if we need to click a pickup filter button
                pickup_btn = await page.query_selector('button:has-text("Pickup")')
                if pickup_btn:
                    print("   Found pickup filter button - clicking it...")
                    await pickup_btn.click()
                    await asyncio.sleep(3)
                    product_cards = await page.query_selector_all('[data-test="product-pod"]')
                    print(f"   After clicking pickup: {len(product_cards)} product cards")

        await page.screenshot(path="test_persistent_no_params.png")
        await asyncio.sleep(2)
        await context.close()

asyncio.run(test())
