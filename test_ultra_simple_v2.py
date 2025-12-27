"""
ULTRA SIMPLE TEST V2 - Check what we actually got
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("\n1. Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        print(f"   Title: {await page.title()}")

        print("\n2. Loading Clearance category...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607", wait_until="domcontentloaded")

        # Wait longer for page to fully load
        await asyncio.sleep(5)

        title = await page.title()
        url = page.url
        print(f"   Title: '{title}'")
        print(f"   URL: {url}")

        if "Access Denied" in title:
            print("   [BLOCKED]")
        else:
            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   Product cards: {len(product_cards)}")

            if len(product_cards) == 0:
                # Check what's on the page
                h1 = await page.query_selector("h1")
                if h1:
                    h1_text = await h1.inner_text()
                    print(f"   H1: {h1_text}")

                # Check for any text that might indicate blocking or error
                content = await page.content()
                if "access denied" in content.lower():
                    print("   [BLOCKED - found 'access denied' in content]")
                elif "robot" in content.lower() or "automated" in content.lower():
                    print("   [BLOCKED - bot detection in content]")
                else:
                    print(f"   [INFO] Page loaded but no products (content length: {len(content)})")
                    # Save for inspection
                    with open("ultra_simple_page.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    print("   Saved HTML to ultra_simple_page.html")
            else:
                print(f"   [SUCCESS] Found {len(product_cards)} products!")
                for i, card in enumerate(product_cards[:3]):
                    try:
                        title_el = await card.query_selector("a[href*='/pd/']")
                        if title_el:
                            text = await title_el.inner_text()
                            print(f"   Product {i+1}: {text[:50]}")
                    except:
                        pass

        await page.screenshot(path="ultra_simple.png")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(test())
