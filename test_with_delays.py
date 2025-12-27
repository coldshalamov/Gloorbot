"""
Test with longer delays - maybe we're navigating too fast after store context
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # Apply stealth
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("1. Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print(f"   Title: {await page.title()}")

        print("\n2. Setting store context...")
        # Click store button
        try:
            store_btn = await page.wait_for_selector('[data-testid*="store"]', timeout=5000)
            await store_btn.click()
            await asyncio.sleep(2)

            # Enter ZIP
            zip_input = await page.wait_for_selector('input[placeholder*="ZIP"]', timeout=5000)
            await zip_input.fill("98144")
            await asyncio.sleep(1)
            await zip_input.press("Enter")
            await asyncio.sleep(5)  # Wait longer for store to set
            print("   Store context set")
        except Exception as e:
            print(f"   Warning: {e}")

        print("\n3. Waiting 10 seconds before category navigation...")
        await asyncio.sleep(10)

        print("\n4. Navigating to Clearance...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607?pickupType=pickupToday&availability=pickupToday&inStock=1"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # DON'T wait for networkidle - that's when it blocks
        print("   NOT waiting for networkidle...")
        await asyncio.sleep(5)

        title = await page.title()
        print(f"\n5. Page title: {title}")

        if "Access Denied" in title:
            print("   [BLOCKED]")
        else:
            # Check for products
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   [SUCCESS] Found {len(product_cards)} product cards")

        await page.screenshot(path="test_with_delays.png")
        await browser.close()

asyncio.run(test())
