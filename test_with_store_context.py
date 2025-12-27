"""
Test scraping WITH store context set first (like the working version does)
"""

import asyncio
from playwright.async_api import async_playwright

# Simplified store context setup
async def set_store_context_simple(page, zip_code="98144"):
    """Set store context like the working version does."""
    print(f"\nSetting store context for ZIP: {zip_code}")

    # Go to homepage
    print("Loading homepage...")
    await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # Look for store selector button
    print("Looking for store selector...")
    store_button_selectors = [
        'button:has-text("Set Store")',
        'button:has-text("My Store")',
        'a:has-text("Change Store")',
        '[data-testid*="store"]',
    ]

    for selector in store_button_selectors:
        try:
            button = await page.wait_for_selector(selector, timeout=3000)
            if button:
                print(f"Found store button: {selector}")
                await button.click()
                await asyncio.sleep(1)
                break
        except:
            continue

    # Enter ZIP code
    print("Entering ZIP code...")
    zip_selectors = [
        'input[name*="zip"]',
        'input[id*="zip"]',
        'input[placeholder*="ZIP"]',
    ]

    for selector in zip_selectors:
        try:
            zip_input = await page.wait_for_selector(selector, timeout=5000)
            if zip_input:
                print(f"Found ZIP input: {selector}")
                await zip_input.fill(zip_code)
                await asyncio.sleep(0.5)
                await zip_input.press("Enter")
                await asyncio.sleep(3)
                print("Store context set!")
                return
        except:
            continue

    print("Could not set store context - continuing anyway")


async def test_category_with_context():
    """Test category scraping AFTER setting store context."""
    print("="*60)
    print("TEST: Category Scrape WITH Store Context")
    print("="*60)

    async with async_playwright() as p:
        # Apply stealth to the entire Playwright instance FIRST (like working version)
        print("\nApplying stealth...")
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.hook_playwright_context(p)
            print("Stealth applied to Playwright instance")
        except Exception as e:
            print(f"Warning: Could not apply stealth: {e}")

        # Launch browser (simple, like working version)
        print("\nLaunching browser...")
        browser = await p.chromium.launch(
            headless=False,
        )

        page = await browser.new_page(
            viewport={"width": 1440, "height": 900}
        )

        try:
            # STEP 1: Set store context FIRST
            await set_store_context_simple(page, "98144")

            # STEP 2: NOW navigate to category WITH PICKUP PARAMS (like working version)
            print("\nNavigating to Clearance category...")
            base_url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
            # Add pickup filter params like the working version does!
            url = f"{base_url}?pickupType=pickupToday&availability=pickupToday&inStock=1&offset=0"
            print(f"URL with params: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Check if we got through
            title = await page.title()
            print(f"\nPage title: {title}")

            if "Access Denied" in title:
                print("\n[FAIL] STILL BLOCKED")
                await page.screenshot(path="test_with_context_blocked.png")
            else:
                print("\n[SUCCESS] NOT BLOCKED!")

                # Check for products
                product_cards = await page.query_selector_all('[data-test="product-pod"]')
                print(f"Found {len(product_cards)} product cards")

                await page.screenshot(path="test_with_context_success.png")

        finally:
            await browser.close()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_category_with_context())
