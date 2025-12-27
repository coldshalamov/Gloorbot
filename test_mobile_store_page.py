"""
Test the ACTUAL working approach from parallel_scraper.py:
1. Mobile device emulation
2. Visit STORE PAGE directly (not homepage)
3. Click "Set as My Store" button
4. Add sn cookie manually
5. Then navigate to category pages
"""

import asyncio
import random
from playwright.async_api import async_playwright

async def test():
    # Use a real store from Washington (Spokane Valley from LowesMap.txt)
    store_url = "https://www.lowes.com/store/WA-Spokane-Valley/2793"
    store_id = "2793"

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

        print(f"Launching browser...")
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

        print(f"\n1. Loading STORE PAGE directly: {store_url}")
        try:
            await page.goto(store_url, wait_until="domcontentloaded", timeout=60000)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except:
                pass  # Safe wait like working scraper
            await asyncio.sleep(2)
            title = await page.title()
            print(f"   Title: {title}")
        except Exception as e:
            print(f"   Error loading store page: {e}")

        print("\n2. Looking for 'Set as My Store' button...")
        button_selectors = [
            "button:has-text('Set as My Store')",
            "button:has-text('Set Store')",
            "button:has-text('Make This My Store')",
            "a:has-text('Set as My Store')",
            "[data-testid*='set-store']",
            "[data-test-id*='set-store']",
            "button:has-text('My Store')",
        ]

        button_clicked = False
        for selector in button_selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=8000)
                if button:
                    await button.click()
                    button_clicked = True
                    print(f"   Clicked button via selector: {selector}")
                    break
            except:
                continue

        if not button_clicked:
            print("   WARNING: Could not find 'Set as My Store' button")

        print(f"\n3. Adding sn cookie for store {store_id}...")
        try:
            await context.add_cookies(
                [{"name": "sn", "value": store_id, "domain": ".lowes.com", "path": "/"}]
            )
            print(f"   Cookie added")
        except Exception as e:
            print(f"   Could not add cookie: {e}")

        await asyncio.sleep(2)

        print("\n4. NOW navigating to Clearance category...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
        print(f"   URL: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass  # Safe wait

        await asyncio.sleep(3)

        try:
            cat_title = await page.title()
            print(f"\n5. Category page title: {cat_title}")

            if "Access Denied" in cat_title:
                print("   [BLOCKED] Category page blocked")
            else:
                product_cards = await page.query_selector_all('[data-test="product-pod"]')
                print(f"   [SUCCESS] Found {len(product_cards)} product cards")

                if len(product_cards) > 0:
                    # Extract first 5 products
                    for i, card in enumerate(product_cards[:5]):
                        try:
                            title_el = await card.query_selector("a[href*='/pd/']")
                            title_text = await title_el.inner_text() if title_el else "Unknown"

                            price_el = await card.query_selector("[data-testid*='price']")
                            price_text = await price_el.inner_text() if price_el else "$0"

                            print(f"   Product {i+1}: {title_text[:50]} - {price_text}")
                        except Exception as e:
                            print(f"   Could not extract product {i+1}: {e}")
                else:
                    print("   WARNING: Page loaded but no product cards found")
                    # Check for no results message
                    content = await page.content()
                    if "no products" in content.lower() or "0 results" in content.lower():
                        print("   INFO: No products available for this store")
        except Exception as e:
            print(f"   ERROR: {e}")

        await page.screenshot(path="test_mobile_store_page.png")
        await asyncio.sleep(2)
        await browser.close()

asyncio.run(test())
