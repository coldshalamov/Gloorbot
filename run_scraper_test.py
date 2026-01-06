#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

os.environ["DEAL_THRESHOLD"] = "0.05"
sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

async def main():
    from scraper import (
        warmup_session,
        set_store_context,
        scrape_category_all_pages,
        Actor,
    )
    from playwright.async_api import async_playwright

    print("Starting Lowe's scraper test with 5% threshold")
    print("=" * 80)

    try:
        # Use specific categories that are known to have deals
        # You can modify these URLs
        store = {
            "name": "Test Store",
            "store_id": "2250",
            "url": "https://www.lowes.com/l/stores/2250",
        }

        # Test category - dishwashers (has discounts visible in screenshot)
        categories = [
            "https://www.lowes.com/pl/dishwashers/4294857925?goToProdList=true&inStock=1&rollUpVariants=0",
        ]

        print(f"\n[1] Test configuration:")
        print(f"    Store: {store['name']} ({store['store_id']})")
        print(f"    Categories: {categories}")

        async with async_playwright() as p:
            print(f"\n[2] Setting up browser...")
            profile_dir = Path(f".playwright-profiles/store-{store['store_id']}")
            profile_dir.mkdir(parents=True, exist_ok=True)

            launch_kwargs = {
                "headless": False,
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

                print(f"[4] Setting store context...")
                await set_store_context(page, store["url"], store["name"])

                print(f"\n[5] Scraping {len(categories)} category...")
                all_products = []

                for cat_url in categories:
                    print(f"\n    Category: {cat_url}")
                    products = await scrape_category_all_pages(page, cat_url, store)
                    print(f"    -> Found {len(products)} products")

                    if products:
                        print(f"\n    Sample products from this category:")
                        for p in products[:10]:
                            title = p.get("title", "Unknown")[:60]
                            price = p.get("price", "N/A")
                            was_price = p.get("was_price", "N/A")
                            print(f"      - {title}")
                            print(f"        Current: {price}, Was: {was_price}")

                    all_products.extend(products)

                print(f"\n[6] Summary: Total products extracted: {len(all_products)}")

                if all_products:
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
                        print(f"\n    All discounted products:")
                        for i, (pct, p) in enumerate(with_discounts, 1):
                            title = p.get("title", "Unknown")[:50]
                            price = parse_price(p.get("price"))
                            was = parse_price(p.get("was_price"))
                            if price and was:
                                print(f"      {i:2d}. {pct*100:5.1f}% off: {title}")
                                print(f"          ${price:.2f} (was ${was:.2f})")
                    else:
                        print("\n    No discounts found. If this is wrong, the extraction might be broken.")

                print("\n" + "=" * 80)
                print("Test complete!")

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
