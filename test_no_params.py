"""
Test WITHOUT pickup filter URL params - just plain category URL
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        print("Setting store context...")
        try:
            store_btn = await page.wait_for_selector('[data-testid*="store"]', timeout=5000)
            await store_btn.click()
            await asyncio.sleep(1)

            zip_input = await page.wait_for_selector('input[placeholder*="ZIP"]', timeout=5000)
            await zip_input.fill("98144")
            await asyncio.sleep(0.5)
            await zip_input.press("Enter")
            await asyncio.sleep(3)
            print("Store context set")
        except Exception as e:
            print(f"Warning: {e}")

        print("\nNavigating to Clearance (NO PARAMS)...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
        print(f"URL: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Don't wait for networkidle
        await asyncio.sleep(5)

        title = await page.title()
        print(f"\nPage title: {title}")

        if "Access Denied" in title:
            print("[BLOCKED]")
        else:
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"[SUCCESS] Found {len(product_cards)} product cards")

        await page.screenshot(path="test_no_params.png")
        await browser.close()

asyncio.run(test())
