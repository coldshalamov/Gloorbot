"""
Test which selector actually gets products with the working approach
"""

import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE_DIR = "C:/Users/User/Documents/GitHub/Telomere/Gloorbot/.playwright-profiles/selector_test"
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
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
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

        # Warmup
        print("\n1. Homepage warmup...")
        await page.goto('https://www.lowes.com', wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3 + random.random() * 2)
        await human_mouse_move(page)
        await asyncio.sleep(1 + random.random())
        await human_scroll(page)
        await asyncio.sleep(1.5 + random.random() * 1.5)

        # Navigate to products
        print("\n2. Loading product page...")
        await page.goto(TEST_URL, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(1 + random.random())
        await human_mouse_move(page)
        await human_scroll(page)
        await asyncio.sleep(2)

        title = await page.title()
        print(f"   Title: {title}")

        if 'Access Denied' in title:
            print("   [BLOCKED]")
        else:
            # Test the main.js selector
            js_selector = "[data-test='product-pod'], [data-test='productPod'], div[data-itemid], li[data-itemid], [data-itemid], li:has(a[href*='/pd/']), article:has(a[href*='/pd/'])"

            print(f"\n3. Testing selector from main.js:")
            print(f"   Selector: {js_selector[:80]}...")

            cards = await page.locator(js_selector).all()
            print(f"   Found: {len(cards)} products")

            # Try to extract from first few
            extracted = 0
            for i, card in enumerate(cards[:5]):
                try:
                    # Use main.js selectors
                    title_selector = ":scope [data-testid='item-description'], :scope a[data-testid='item-description-link'], :scope a[href*='/pd/'], :scope [data-test*='product-title'], :scope h3, :scope h2"
                    link_selector = ":scope a[data-testid='item-description-link'], :scope a[href*='/pd/'], :scope a[data-test*='product-link']"

                    title_el = card.locator(title_selector).first
                    link_el = card.locator(link_selector).first

                    title_text = ""
                    href = ""

                    if await title_el.count() > 0:
                        title_text = await title_el.inner_text()
                    if await link_el.count() > 0:
                        href = await link_el.get_attribute("href") or ""

                    if title_text and href:
                        extracted += 1
                        print(f"   Product {extracted}: {title_text[:50]}...")
                    else:
                        print(f"   Product {i+1}: Failed (title={bool(title_text)}, href={bool(href)})")

                except Exception as e:
                    print(f"   Product {i+1}: Error - {e}")

            print(f"\n   Successfully extracted: {extracted}/{len(cards)}")

        await asyncio.sleep(10)
        await context.close()

asyncio.run(test())
