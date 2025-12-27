"""
Test WITH mobile device emulation (the ACTUAL working approach!)
Key: Use mobile device emulation instead of persistent context
"""

import asyncio
import random
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # Apply stealth to Playwright instance BEFORE launch
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        # Pick a random mobile device (like working scraper)
        mobile_devices = [
            "Pixel 5",
            "Pixel 7",
            "Galaxy S9+",
            "Galaxy S20",
            "iPhone 11",
            "iPhone 12",
            "iPhone 13",
            "iPhone 14",
        ]
        device_name = random.choice(mobile_devices)
        device = p.devices[device_name]

        print(f"Using mobile device: {device_name}")

        # Randomize viewport slightly (like working scraper)
        viewport = device["viewport"].copy()
        viewport["width"] = viewport.get("width", 375) + random.randint(-20, 20)
        viewport["height"] = viewport.get("height", 667) + random.randint(-50, 50)

        print(f"Launching browser with mobile emulation...")
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=12,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
                "--start-maximized",
                "--window-size=1440,960",
            ]
        )

        # Create context with mobile device settings
        context = await browser.new_context(
            viewport=viewport,
            user_agent=device.get("userAgent"),
            device_scale_factor=device.get("deviceScaleFactor"),
            is_mobile=device.get("isMobile", True),
            has_touch=device.get("hasTouch", True),
        )

        page = await context.new_page()

        print("\n1. Loading Lowe's homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        title = await page.title()
        print(f"   Title: {title}")

        if "Access Denied" in title:
            print("   [BLOCKED] Homepage blocked")
        else:
            print("   [SUCCESS] Homepage loaded!")

            # Now try loading a category page WITHOUT setting store context first
            print("\n2. Loading Clearance category WITHOUT store context...")
            url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
            print(f"   URL: {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            try:
                cat_title = await page.title()
                print(f"   Category title: {cat_title}")

                if "Access Denied" in cat_title:
                    print("   [BLOCKED] Category page blocked")
                else:
                    product_cards = await page.query_selector_all('[data-test="product-pod"]')
                    print(f"   [SUCCESS] Found {len(product_cards)} product cards")

                    if len(product_cards) > 0:
                        # Extract first 3 products
                        for i, card in enumerate(product_cards[:3]):
                            try:
                                title_el = await card.query_selector("a[href*='/pd/']")
                                title_text = await title_el.inner_text() if title_el else "Unknown"
                                print(f"   Product {i+1}: {title_text[:50]}")
                            except Exception as e:
                                print(f"   Could not extract product {i+1}: {e}")
            except Exception as e:
                print(f"   ERROR: {e}")

        await page.screenshot(path="test_mobile_emulation.png")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(test())
