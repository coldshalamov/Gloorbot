"""
EXACT conversion of test_final.js to Python
The JS version works - let's see if Python does too
"""

import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE_DIR = "C:/Users/User/Documents/GitHub/Telomere/Gloorbot/apify_actor_seed/.playwright-profiles/test_final"
TEST_URL = "https://www.lowes.com/pl/paint-cleaners-chemicals-additives/2521972965619"

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
    print("=" * 60)
    print("AKAMAI BYPASS - PYTHON VERSION OF test_final.js")
    print("=" * 60)

    # Ensure profile exists
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    print(f"\nUsing profile: {PROFILE_DIR}")

    async with async_playwright() as p:
        # DO NOT apply stealth here - JS version doesn't use it!
        # The JS version relies ONLY on persistent profile + Chrome + human behavior

        print("Launching Chrome with persistent profile...\n")

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

        try:
            # STEP 1: Homepage warmup
            print("1. Loading homepage first (session warm-up)...")
            await page.goto('https://www.lowes.com',
                          wait_until='domcontentloaded',
                          timeout=60000)
            await asyncio.sleep(3 + random.random() * 2)

            home_title = await page.title()
            print(f'   Title: "{home_title}"')

            content = await page.content()
            if 'Access Denied' in content:
                print('   BLOCKED on homepage!')
                await context.close()
                return

            # STEP 2: Human behavior
            print("\n2. Simulating human behavior...")
            await human_mouse_move(page)
            await asyncio.sleep(1 + random.random())
            await human_scroll(page)
            await asyncio.sleep(1.5 + random.random() * 1.5)
            await human_mouse_move(page)
            print("   Done.")

            # STEP 3: Navigate to product page
            print("\n3. Navigating to product listing...")
            await page.goto(TEST_URL,
                          wait_until='domcontentloaded',
                          timeout=60000)

            await asyncio.sleep(1 + random.random())
            await human_mouse_move(page)
            await human_scroll(page)
            await asyncio.sleep(2)

            title = await page.title()
            url = page.url

            print(f'   Title: "{title}"')
            print(f'   URL: {url}')

            # Check results
            content = await page.content()
            blocked = 'Access Denied' in content or 'Access Denied' in title

            print("\n" + "=" * 60)
            if blocked:
                print("RESULT: BLOCKED")
            elif '404' in title:
                print("RESULT: 404 (URL changed)")
            else:
                print("RESULT: SUCCESS!")

                # Count products
                selectors = ['article', '[class*="ProductCard"]', '[class*="product-card"]']
                print("\nProduct counts:")
                for sel in selectors:
                    count = await page.locator(sel).count()
                    if count > 0:
                        print(f"  {sel}: {count} elements")

            print("=" * 60)

            print("\nBrowser stays open for 15 seconds...")
            await asyncio.sleep(15)

        except Exception as err:
            print(f"\nError: {err}")
        finally:
            await context.close()

asyncio.run(test())
