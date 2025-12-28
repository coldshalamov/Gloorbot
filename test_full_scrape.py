"""
Final test of the PARALLEL scraper with all fixes applied
"""
import asyncio
import sys
from pathlib import Path

# Add PARALLEL to path
parallel_dir = Path(__file__).parent / "PARALLEL"
sys.path.insert(0, str(parallel_dir))

from playwright.async_api import async_playwright


async def main():
    # Import the scraper functions
    import importlib.util
    scraper_path = parallel_dir / "scraper.py"
    spec = importlib.util.spec_from_file_location("parallel_scraper", str(scraper_path))
    scraper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scraper)

    profile_dir = Path(".playwright-profiles/test-final")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        launch_kwargs = {
            "headless": False,
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
            ],
        }

        try:
            context = await p.chromium.launch_persistent_context(str(profile_dir), channel="chrome", **launch_kwargs)
            print("[INFO] Using Chrome")
        except Exception as e:
            print(f"[INFO] Chrome not available ({e}), using Chromium")
            context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Step 1: Warmup
            print("\n" + "="*60)
            print("STEP 1: Warming up session")
            print("="*60)
            await scraper.warmup_session(page)

            # Step 2: Set store
            print("\n" + "="*60)
            print("STEP 2: Setting store")
            print("="*60)
            store_info = {
                "store_id": "0004",
                "name": "Seattle, WA (#0004)",
                "city": "Seattle",
                "state": "WA",
                "url": "https://www.lowes.com/store/WA-Seattle/0004"
            }
            await scraper.set_store_context(page, store_info["url"], store_info["name"])

            # Step 3: Scrape a category (just first page)
            print("\n" + "="*60)
            print("STEP 3: Scraping category (Power Tools) - single page")
            print("="*60)

            # Use the scrape_category_page directly to test one page
            category_url = "https://www.lowes.com/pl/Power-tools-Tools/4294607842"

            # Apply pickup filter first
            await page.goto(category_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)
            await scraper.human_mouse_move(page)
            await asyncio.sleep(0.5)

            filter_applied = await scraper.apply_pickup_filter(page, "test-category")
            print(f"[INFO] Pickup filter applied: {filter_applied}")

            if filter_applied:
                # Get updated URL with filter
                filtered_url = page.url
                print(f"[INFO] Filtered URL: {filtered_url[:80]}...")

                # Scrape single page
                products = await scraper.scrape_category_page(page, filtered_url, store_info, page_num=1)

                print("\n" + "="*60)
                print("RESULTS")
                print("="*60)
                print(f"Total products found on page 1: {len(products)}")

                if products:
                    # Show first 5 products
                    print("\nFirst 5 products:")
                    for i, prod in enumerate(products[:5]):
                        print(f"\n  {i+1}. {prod.get('title', 'N/A')[:50]}...")
                        print(f"     Price: {prod.get('price', 'N/A')}")
                        print(f"     Was: {prod.get('was_price', 'N/A')}")
                        print(f"     Markdown: {prod.get('has_markdown', False)}")

                    # Count markdowns
                    markdowns = [p for p in products if p.get('has_markdown')]
                    print(f"\nProducts with markdowns: {len(markdowns)} / {len(products)}")

                    # Show 50%+ deals
                    deals_50 = []
                    for p in products:
                        try:
                            price = float(str(p.get('price', '')).replace('$', '').replace(',', ''))
                            was = float(str(p.get('was_price', '')).replace('$', '').replace(',', ''))
                            if was > 0 and price < was:
                                pct = (was - price) / was * 100
                                if pct >= 50:
                                    deals_50.append({**p, 'pct_off': pct})
                        except:
                            pass

                    print(f"\n50%+ OFF DEALS: {len(deals_50)}")
                    for d in deals_50[:3]:
                        print(f"  - {d['title'][:40]}: {d['price']} (was {d['was_price']}, {d['pct_off']:.0f}% off)")
                else:
                    print("\nNO PRODUCTS FOUND!")
            else:
                print("\n[ERROR] Pickup filter not applied!")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n[INFO] Closing browser...")
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
