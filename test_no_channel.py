"""
Test WITHOUT specifying channel parameter (let Playwright use default)
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        # NO channel parameter - let it use default
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Loading category page...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607",
                       wait_until="domcontentloaded",
                       timeout=60000)

        await asyncio.sleep(3)

        title = await page.title()
        print(f"Title: {title}")

        if "Access Denied" in title:
            print("[BLOCKED]")
        else:
            cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"[{len(cards)} products]")

        await browser.close()

asyncio.run(test())
