"""
Test WITH persistent browser context (like working Cheapskater version)
Key: Use launch_persistent_context to reuse browser profile with cookies/session
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def safe_wait_for_load(page, state):
    """Match Cheapskater's _safe_wait_for_load - silently continue on timeout"""
    try:
        await page.wait_for_load_state(state)
    except Exception:
        return

async def jitter_mouse(page):
    """Randomize cursor movement to mimic human browsing (from Cheapskater)"""
    import random
    try:
        width = await page.evaluate("() => window.innerWidth || 1280")
        height = await page.evaluate("() => window.innerHeight || 800")
    except:
        width, height = 1280, 800

    try:
        for _ in range(random.randint(1, 3)):
            target_x = random.randint(0, int(max(width, 1)))
            target_y = random.randint(0, int(max(height, 1)))
            steps = random.randint(3, 7)
            await page.mouse.move(target_x, target_y, steps=steps)
            await asyncio.sleep(random.uniform(0.12, 0.32))
    except:
        return

async def test():
    # Create persistent profile directory
    profile_dir = Path("c:/Users/User/Documents/GitHub/Telomere/Gloorbot/.playwright-profile")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Apply stealth to Playwright instance BEFORE launch
        from playwright_stealth import Stealth
        stealth = Stealth()
        stealth.hook_playwright_context(p)

        print(f"Launching Chromium with persistent context...")
        print(f"Profile dir: {profile_dir}")

        # Use launch_persistent_context like Cheapskater does
        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            slow_mo=12,  # CRITICAL: Slow down actions to look human
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
                "--start-maximized",
                "--window-size=1440,960",
            ],
            viewport={"width": 1440, "height": 900}
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print("\n1. Loading homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        await jitter_mouse(page)  # Move mouse randomly
        print(f"   Title: {await page.title()}")

        print("\n2. Setting store context...")
        try:
            store_btn = await page.wait_for_selector('[data-testid*="store"]', timeout=5000)
            await store_btn.click()
            await asyncio.sleep(1)

            zip_input = await page.wait_for_selector('input[placeholder*="ZIP"]', timeout=5000)
            await zip_input.fill("98144")
            await asyncio.sleep(0.5)
            await zip_input.press("Enter")
            await asyncio.sleep(3)
            print("   Store context set")
        except Exception as e:
            print(f"   Warning: {e}")

        print("\n3. Navigating to Clearance with pickup filter params...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607?pickupType=pickupToday&availability=pickupToday&inStock=1&offset=0"
        print(f"   URL: {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Use safe wait like Cheapskater does
        print("   Waiting for networkidle (with safe catch)...")
        await safe_wait_for_load(page, "networkidle")
        await asyncio.sleep(2)
        await jitter_mouse(page)  # Move mouse randomly

        try:
            title = await page.title()
            print(f"\n4. Page title: {title}")
        except Exception as e:
            print(f"\n4. Could not get title (page destroyed): {e}")
            title = "ERROR"

        if "Access Denied" in title:
            print("   [BLOCKED] Got Access Denied")
        else:
            # Wait a bit more for products to load
            print("   Waiting for products to load...")
            await asyncio.sleep(3)

            product_cards = await page.query_selector_all('[data-test="product-pod"]')
            print(f"   Found {len(product_cards)} product cards")

            if len(product_cards) == 0:
                # Check if there's a "no results" message
                content = await page.content()
                if "no products found" in content.lower() or "0 results" in content.lower():
                    print("   [INFO] Pickup filter may be too restrictive - no products available")
                else:
                    print("   [WARNING] Page loaded but no product cards found")
                    # Save HTML for inspection
                    with open("test_persistent_debug.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    print("   Saved HTML to test_persistent_debug.html")
            else:
                print(f"   [SUCCESS] Found {len(product_cards)} products!")
                # Extract first few products to verify
                for i, card in enumerate(product_cards[:3]):
                    try:
                        title_el = await card.query_selector("a[href*='/pd/']")
                        title_text = await title_el.inner_text() if title_el else "Unknown"
                        print(f"   Product {i+1}: {title_text[:60]}")
                    except Exception as e:
                        print(f"   Could not extract product {i+1}: {e}")

        await page.screenshot(path="test_persistent_context.png")
        await asyncio.sleep(2)
        await context.close()

asyncio.run(test())
