"""
CRITICAL: Visit homepage FIRST before category pages
From AKAMAI_BYPASS_KNOWLEDGE.md lines 11-16
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

        # CRITICAL: Visit homepage FIRST
        print("1. Visiting homepage FIRST (warming up session)...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=60000)

        # Wait 3-5 seconds for Akamai challenge
        print("   Waiting 5 seconds for Akamai challenge...")
        await asyncio.sleep(5)

        homepage_title = await page.title()
        print(f"   Homepage: {homepage_title}")

        # NOW navigate to category
        print("\n2. NOW navigating to category page...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607",
                       wait_until="domcontentloaded",
                       timeout=60000)

        await asyncio.sleep(3)

        title = await page.title()
        print(f"   Category: {title}")

        if "Access Denied" in title:
            print("\n[BLOCKED]")
        else:
            cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"\n[SUCCESS] {len(cards)} products")

        await browser.close()

asyncio.run(test())
