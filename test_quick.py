"""
Quick test - 1 store, 1 category, 2 pages max
Tests if the scraper works from residential IP
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add the actor src to path
sys.path.insert(0, str(Path(__file__).parent / "apify_actor_seed" / "src"))

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def test_single_page():
    """Test scraping a single Lowe's category page"""

    async with async_playwright() as pw:
        # Launch browser
        browser = await pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # Create context
        context = await browser.new_context()

        # Apply stealth to context
        stealth = Stealth()
        stealth.apply_stealth_sync(context)

        page = await context.new_page()

        # Block resources
        async def handle_route(route):
            if any(x in route.request.url for x in ['.jpg', '.png', '.gif', '.css', '.woff', '.ttf']):
                await route.abort()
            else:
                await route.continue_()

        await page.route('**/*', handle_route)

        try:
            # Navigate to Clearance category for Seattle store
            url = "https://www.lowes.com/pl/The-back-aisle/2021454685607?location=98144"
            print(f"\n[TEST] Navigating to: {url}")

            response = await page.goto(url, wait_until="networkidle", timeout=60000)
            print(f"[TEST] Response status: {response.status}")

            if response.status == 403:
                print("[TEST] ❌ BLOCKED BY AKAMAI (403)")
                return False

            # Wait a bit for content to load
            await asyncio.sleep(2)

            # Try to apply pickup filter
            print("[TEST] Applying pickup filter...")
            filter_selectors = [
                'label:has-text("Get it Today")',
                'label:has-text("Available Today")',
                'label:has-text("Pickup available")',
                'input[aria-label*="Get it Today"]',
                'input[aria-label*="Available Today"]',
            ]

            filter_applied = False
            for selector in filter_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        filter_applied = True
                        print(f"[TEST] ✓ Filter applied with selector: {selector}")
                        break
                except Exception as e:
                    continue

            if not filter_applied:
                print("[TEST] ⚠ Could not apply filter, but continuing...")

            # Try different product selectors
            products = await page.evaluate("""
            () => {
                // Try multiple selectors
                let items = document.querySelectorAll('[data-test="product-item"]');
                if (items.length === 0) items = document.querySelectorAll('article[data-test]');
                if (items.length === 0) items = document.querySelectorAll('div[class*="ProductCard"]');
                if (items.length === 0) items = document.querySelectorAll('[class*="product"]');

                return Array.from(items).slice(0, 5).map((item, i) => {
                    return {
                        index: i,
                        html: item.outerHTML.substring(0, 200)
                    };
                });
            }
            """)

            print(f"[TEST] Found {len(products)} elements:")
            for i, p in enumerate(products, 1):
                print(f"  {i}. {p['html']}")

            if len(products) > 0:
                print("[TEST] ✓ SUCCESS - Page loaded and products found")
                return True
            else:
                print("[TEST] ⚠ No products found (may be filter issue)")
                return False

        except Exception as e:
            print(f"[TEST] ❌ Error: {e}")
            return False
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_single_page())
    sys.exit(0 if result else 1)
