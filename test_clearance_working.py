"""
WORKING approach applied to Clearance category
NO playwright-stealth, just Chrome + persistent profile + warmup
"""

import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE_DIR = "C:/Users/User/Documents/GitHub/Telomere/Gloorbot/.playwright-profiles/clearance_test"

async def human_mouse_move(page):
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
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep((15 + random.random() * 25) / 1000)

async def human_scroll(page):
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((40 + random.random() * 80) / 1000)

async def test():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # NO playwright-stealth!

        print("Launching Chrome...")
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            channel='chrome',
            viewport={'width': 1440, 'height': 900},
            locale='en-US',
            timezone_id='America/Los_Angeles',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-infobars',
            ]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Warmup on homepage
        print("\n1. Homepage warmup...")
        await page.goto('https://www.lowes.com', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3 + random.random() * 2)
        await human_mouse_move(page)
        await asyncio.sleep(1 + random.random())
        await human_scroll(page)
        await asyncio.sleep(1.5 + random.random() * 1.5)

        # Navigate to Clearance
        print("\n2. Loading Clearance...")
        await page.goto('https://www.lowes.com/pl/The-back-aisle/2021454685607',
                      wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(1 + random.random())
        await human_mouse_move(page)
        await human_scroll(page)
        await asyncio.sleep(2)

        title = await page.title()
        print(f"   Title: {title}")

        if 'Access Denied' in title:
            print("   [BLOCKED]")
        else:
            cards = await page.locator('[data-test="product-pod"]').count()
            print(f"   [SUCCESS] {cards} products!")

        await asyncio.sleep(10)
        await context.close()

asyncio.run(test())
