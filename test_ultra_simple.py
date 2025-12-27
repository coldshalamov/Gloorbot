"""
ULTRA SIMPLE TEST - Strip away ALL the "anti-detection" features
Just use playwright-stealth and nothing else
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # ONLY apply stealth - nothing else
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print("Launching browser (simple)...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("\n1. Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        print(f"   Title: {await page.title()}")

        print("\n2. Loading Clearance category...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607", wait_until="domcontentloaded")

        title = await page.title()
        print(f"   Title: {title}")

        if "Access Denied" in title:
            print("   [BLOCKED]")
        else:
            await asyncio.sleep(3)  # Just wait a bit for products
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   [SUCCESS] Found {len(product_cards)} product cards")

        await browser.close()

asyncio.run(test())
