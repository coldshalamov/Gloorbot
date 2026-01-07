"""
Quick local test script for scraper.py changes.

Run this to test scraper logic WITHOUT rebuilding the worker.
Just edit scraper.py and run: python test_scraper_local.py
"""

import asyncio
import sys
from pathlib import Path

# Import the scraper module directly
sys.path.insert(0, str(Path(__file__).parent))
from scraper import (
    load_stores_and_categories,
    warmup_session,
    set_store_context,
    scrape_category_all_pages,
)
from playwright.async_api import async_playwright


async def test_single_category():
    """Test a single store + category to verify scraper behavior quickly."""

    # Load stores and categories
    all_stores, all_categories = load_stores_and_categories()

    # Pick first WA/OR store
    test_store = None
    for store in all_stores:
        if store["state"] in ["WA", "OR"]:
            test_store = store
            break

    if not test_store:
        print("No WA/OR stores found!")
        return

    # Pick first category (or specify one that's likely to have deals)
    test_category = all_categories[0] if all_categories else None

    if not test_category:
        print("No categories found!")
        return

    print("=" * 70)
    print(f"LOCAL TEST RUN")
    print("=" * 70)
    print(f"Store: {test_store['name']}")
    print(f"Category: {test_category}")
    print("=" * 70)

    async with async_playwright() as p:
        # Use a test profile
        profile_dir = Path(".playwright-profiles/test-local")
        profile_dir.mkdir(parents=True, exist_ok=True)

        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,  # Watch it work
            channel="chrome",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Warmup
            print("\n[TEST] Warming up session...")
            await warmup_session(page)

            # Set store
            print(f"\n[TEST] Setting store: {test_store['name']}")
            await set_store_context(page, test_store["url"], test_store["name"])

            # Scrape category
            print(f"\n[TEST] Scraping category...")
            products = await scrape_category_all_pages(page, test_category, test_store)

            print("\n" + "=" * 70)
            print(f"RESULTS: {len(products)} products found")
            print("=" * 70)

            # Show first few products
            for i, product in enumerate(products[:5], 1):
                print(f"\n{i}. {product['title'][:60]}")
                print(f"   Price: {product['price']}")
                if product['was_price']:
                    print(f"   Was: {product['was_price']} (MARKDOWN!)")
                print(f"   URL: {product['url'][:80]}...")

            if len(products) > 5:
                print(f"\n... and {len(products) - 5} more products")

            # Count markdowns
            markdown_count = sum(1 for p in products if p['has_markdown'])
            print(f"\n{markdown_count}/{len(products)} products have markdowns")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await context.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SCRAPER LOCAL TEST")
    print("Tests scraper.py changes WITHOUT rebuilding worker")
    print("=" * 70 + "\n")

    asyncio.run(test_single_category())
