"""
FULL implementation from main.js warmUpSession() function
Lines 704-721 + using channel='chrome'
"""

import asyncio
import random
from playwright.async_api import async_playwright

async def human_mouse_move(page):
    """Human-like mouse movement (from main.js lines 670-691)"""
    viewport = page.viewport_size
    width = viewport.get('width', 1440) if viewport else 1440
    height = viewport.get('height', 900) if viewport else 900

    start_x = random.random() * width * 0.3
    start_y = random.random() * height * 0.3
    end_x = width * 0.4 + random.random() * width * 0.4
    end_y = height * 0.4 + random.random() * height * 0.4

    steps = 10 + int(random.random() * 10)
    for i in range(steps + 1):
        progress = i / steps
        # Ease in-out quad
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep((15 + random.random() * 25) / 1000)

async def human_scroll(page):
    """Human-like scrolling (from main.js lines 694-702)"""
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((40 + random.random() * 80) / 1000)

async def warm_up_session(page):
    """Warm up browser session (from main.js lines 705-721)"""
    print("Warming up browser session...")

    # Load homepage first
    await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)

    # Simulate human behavior
    await human_mouse_move(page)
    await asyncio.sleep(1 + random.random())
    await human_scroll(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)
    await human_mouse_move(page)
    await asyncio.sleep(0.5 + random.random() * 0.5)

    print("Session warm-up complete")

async def test():
    async with async_playwright() as p:
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print("Launching Chrome (not Chromium)...")
        # CRITICAL: Use channel='chrome' like main.js line 753
        browser = await p.chromium.launch(
            headless=False,
            channel='chrome',  # Use real Chrome!
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-infobars',
            ]
        )

        page = await browser.new_page(viewport={'width': 1440, 'height': 900})

        # Warm up session
        await warm_up_session(page)

        # NOW navigate to category
        print("\nNavigating to category page...")
        await page.goto("https://www.lowes.com/pl/The-back-aisle/2021454685607",
                       wait_until='domcontentloaded',
                       timeout=60000)

        await asyncio.sleep(3)

        title = await page.title()
        print(f"Title: {title}")

        if "Access Denied" in title:
            print("\n[BLOCKED]")
        else:
            cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"\n[SUCCESS] {len(cards)} products!")

        await browser.close()

asyncio.run(test())
