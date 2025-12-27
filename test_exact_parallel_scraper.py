"""
EXACT replication of what parallel_scraper.py does - nothing more, nothing less
"""

import asyncio
import random
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        # Step 1: Apply stealth (exact same way)
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        # Step 2: Pick mobile device (exact same way)
        mobile_devices = ["Pixel 5", "Pixel 7", "Galaxy S9+", "Galaxy S20", "iPhone 11", "iPhone 12", "iPhone 13", "iPhone 14"]
        device_name = random.choice(mobile_devices)
        device = p.devices[device_name]

        print(f"Device: {device_name}")

        # Step 3: Build launch options (exact same way)
        launch_opts = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
                "--start-maximized",
                "--window-size=1440,960",
            ]
        }
        # NO channel, NO slow_mo, NO proxy (launch.bat sets these to empty/none)

        # Step 4: Build context options from device (exact same way)
        vp = device["viewport"].copy()
        vp["width"] = vp.get("width", 375) + random.randint(-20, 20)
        vp["height"] = vp.get("height", 667) + random.randint(-50, 50)

        context_opts = {
            "viewport": vp,
            "user_agent": device.get("userAgent"),
            "device_scale_factor": device.get("deviceScaleFactor"),
            "is_mobile": device.get("isMobile", True),
            "has_touch": device.get("hasTouch", True),
        }

        # Step 5: Launch browser + context (exact same way - NO persistent profile)
        browser = await p.chromium.launch(**launch_opts)
        context = await browser.new_context(**context_opts)
        page = await context.new_page()

        # Step 6: Load category page directly (NO homepage, NO store page)
        print("Loading category...")
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
