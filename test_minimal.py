"""
Minimal test - just playwright-stealth, nothing else
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

        print("Loading Clearance page directly...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607",
                       wait_until="domcontentloaded",
                       timeout=60000)

        await asyncio.sleep(5)

        title = await page.title()
        print(f"Title: {title}")

        if "Access Denied" in title or "access denied" in title.lower():
            print("[BLOCKED]")
        else:
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"Product cards: {len(product_cards)}")

            if len(product_cards) > 0:
                print("[SUCCESS - Got products!]")
            else:
                # Check page content
                content = await page.content()
                if "access denied" in content.lower():
                    print("[BLOCKED - in content]")
                else:
                    print(f"[LOADED - but no products, {len(content)} chars]")

        await page.screenshot(path="minimal_test.png")
        await browser.close()

asyncio.run(test())
