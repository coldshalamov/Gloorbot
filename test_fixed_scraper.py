"""
Test the fixed scraper with robust timeout handling
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "apify_actor_seed" / "src"))

from main import (
    load_stores_and_categories,
    warmup_session,
    set_store_context,
    scrape_category_all_pages
)
from playwright.async_api import async_playwright


async def test_scraper():
    """Test scraper with timeouts on a single store/category"""

    # Load stores and categories
    all_stores, all_categories = load_stores_and_categories()

    # Filter WA stores
    wa_stores = [s for s in all_stores if s["state"] == "WA"]

    if not wa_stores:
        print("❌ No WA stores found!")
        return

    if not all_categories:
        print("❌ No categories found!")
        return

    # Test with first store and first 2 categories
    test_store = wa_stores[0]
    test_categories = all_categories[:2]

    print(f"\n{'='*70}")
    print(f"Testing Fixed Scraper")
    print(f"{'='*70}")
    print(f"Store: {test_store['name']}")
    print(f"Categories: {len(test_categories)}")
    print(f"{'='*70}\n")

    async with async_playwright() as p:
        profile_dir = Path(f".playwright-profiles/test-{test_store['store_id']}")
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
            ]
        }

        context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            print("[*] Warming up session...")
            await warmup_session(page)

            print(f"[*] Setting store: {test_store['name']}")
            await set_store_context(page, test_store["url"], test_store["name"])

            total_products = 0
            for idx, category_url in enumerate(test_categories):
                print(f"\n[*] Scraping category {idx+1}/{len(test_categories)}")

                try:
                    # Wrap in timeout to prevent infinite hangs
                    products = await asyncio.wait_for(
                        scrape_category_all_pages(page, category_url, test_store),
                        timeout=300.0  # 5 minute max per category
                    )
                    total_products += len(products)
                    print(f"[+] Scraped {len(products)} products from category {idx+1}")

                except asyncio.TimeoutError:
                    print(f"[!] TIMEOUT on category {idx+1} after 5 minutes")
                    print("[X] This should NOT happen with the fixes - category scraping should fail faster")
                    break
                except Exception as e:
                    print(f"[X] ERROR on category {idx+1}: {e}")
                    # Continue to next category
                    continue

            print(f"\n{'='*70}")
            print(f"[+] Test Complete: {total_products} total products")
            print(f"{'='*70}")

        except Exception as e:
            print(f"\n[X] Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await context.close()
            print("\n[*] Browser closed")


if __name__ == "__main__":
    asyncio.run(test_scraper())
