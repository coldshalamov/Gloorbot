#!/usr/bin/env python3
"""
Run the PARALLEL scraper with test settings and lower threshold.
This is a wrapper that lets you test price extraction locally.
"""

import asyncio
import os
import sys
from pathlib import Path

# Set a lower threshold for testing
os.environ["DEAL_THRESHOLD"] = "0.05"

# Add PARALLEL to path
sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

async def main():
    # Import the scraper
    from scraper import (
        load_stores_and_categories,
        warmup_session,
        set_store_context,
        scrape_category_all_pages,
        Actor,
    )

    from playwright.async_api import async_playwright

    print("Starting Lowe's scraper test with 5% threshold")
    print("=" * 80)

    try:
        # Load stores and categories
        print("\n[1] Loading stores and categories...")
        all_stores, all_categories = load_stores_and_categories()
        print(f"    Found {len(all_stores)} stores and {len(all_categories)} categories")

        # Just use first store and first 2 categories for quick test
        stores = all_stores[:1]  # Just one store
        categories = all_categories[:2]  # Just two categories

        if not stores or not categories:
            print("ERROR: No stores or categories found")
            return

        print(f"    Testing with: {stores[0]['name']} store")
        print(f"    Categories: {', '.join(c for c in categories[:2])}")

        async with async_playwright() as p:
            store = stores[0]

            print(f"\n[2] Setting up browser for {store['name']}...")
            profile_dir = Path(f".playwright-profiles/store-{store['store_id']}")
            profile_dir.mkdir(parents=True, exist_ok=True)

            # Use same config as PARALLEL scraper
            launch_kwargs = {
                "headless": False,  # Must be False - Lowe's blocks headless
                "channel": "chrome",
                "viewport": {"width": 1440, "height": 900},
                "locale": "en-US",
                "timezone_id": "America/Los_Angeles",
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--memory-pressure-off",
                ],
            }

            context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                print("[3] Warming up session...")
                await warmup_session(page)

                print(f"[4] Setting store context for {store['name']}...")
                await set_store_context(page, store["url"], store["name"])

                print(f"\n[5] Scraping {len(categories)} test categories...")
                all_products = []

                for cat_idx, category_url in enumerate(categories, 1):
                    print(f"\n    Category {cat_idx}/{len(categories)}: {category_url}")
                    products = await scrape_category_all_pages(page, category_url, store)
                    print(f"    -> Found {len(products)} products")

                    if products:
                        print(f"\n    First 5 products from this category:")
                        for p in products[:5]:
                            title = p.get("title", "Unknown")[:60]
                            price = p.get("price", "N/A")
                            was_price = p.get("was_price", "N/A")
                            print(f"      - {title}")
                            print(f"        Price: {price}, Was: {was_price}")

                    all_products.extend(products)

                print(f"\n[6] Summary:")
                print(f"    Total products extracted: {len(all_products)}")

                if all_products:
                    # Count how many have both prices
                    with_both = sum(1 for p in all_products if p.get("price") and p.get("was_price"))
                    print(f"    Products with both prices: {with_both}")

                    # Show discount distribution
                    import re

                    def parse_price(text):
                        if not text:
                            return None
                        text = str(text).replace(",", "")
                        m = re.search(r'\$?([\d.]+)', text)
                        return float(m.group(1)) if m else None

                    with_discounts = []
                    for p in all_products:
                        price = parse_price(p.get("price"))
                        was = parse_price(p.get("was_price"))
                        if price and was and was > price:
                            pct = (was - price) / was
                            with_discounts.append((pct, p))

                    print(f"    Products with actual discounts: {len(with_discounts)}")

                    if with_discounts:
                        with_discounts.sort(reverse=True)
                        print(f"\n    Top 10 discounted products:")
                        for i, (pct, p) in enumerate(with_discounts[:10], 1):
                            title = p.get("title", "Unknown")[:50]
                            price = parse_price(p.get("price"))
                            was = parse_price(p.get("was_price"))
                            if price and was:
                                print(f"      {i:2d}. {pct*100:5.1f}% off: {title}")
                                print(f"          ${price:.2f} (was ${was:.2f})")

                print("\n" + "=" * 80)
                print("Test complete! Check the products above.")
                print("If prices look reasonable, the fix is working.")
                print("=" * 80)

            finally:
                await context.close()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
