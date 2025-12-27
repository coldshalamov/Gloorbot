"""
Test using actual browser profile from your laptop
This should have the "trust" built up already
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    # Use one of the working profiles from your laptop
    profile_path = "C:/Users/User/Documents/GitHub/Telomere/Gloorbot/.playwright-profiles/store_0061_1029"

    async with async_playwright() as p:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print(f"Using profile: {profile_path}")
        print("Launching browser with laptop profile...")

        # Use persistent context with the working profile
        context = await p.chromium.launch_persistent_context(
            profile_path,
            headless=False
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print("\nLoading Clearance category...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607",
                       wait_until="domcontentloaded",
                       timeout=60000)

        await asyncio.sleep(3)

        title = await page.title()
        print(f"Title: {title}")

        if "Access Denied" in title:
            print("[BLOCKED - even with laptop profile]")
        else:
            cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"[Found {len(cards)} product cards]")

            if len(cards) > 0:
                print("[SUCCESS!]")
                for i, card in enumerate(cards[:3]):
                    try:
                        title_el = await card.query_selector("a[href*='/pd/']")
                        if title_el:
                            text = await title_el.inner_text()
                            print(f"  Product {i+1}: {text[:50]}")
                    except:
                        pass

        await context.close()

asyncio.run(test())
