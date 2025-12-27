"""
Test: Load category page directly (NO store context, NO params)
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Try 1: Load homepage first
        print("\n1. Loading homepage first...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        print(f"   Homepage title: {await page.title()}")
        await asyncio.sleep(2)

        # Try 2: Now navigate to category
        print("\n2. Navigating to clearance category...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for content to actually load
        print("   Waiting for page to fully load...")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(3)

        title = await page.title()
        print(f"   Category title: {title}")

        # Check for products
        product_cards = await page.query_selector_all('[data-test="product-pod"]')
        print(f"   Found {len(product_cards)} product cards")

        if "Access Denied" in title:
            print("\n   [BLOCKED] Got Access Denied")
        elif len(product_cards) > 0:
            print(f"\n   [SUCCESS] Page loaded with {len(product_cards)} products!")
        else:
            print("\n   [PARTIAL] Page loaded but no products found")

        await page.screenshot(path="test_direct_category.png")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(test())
