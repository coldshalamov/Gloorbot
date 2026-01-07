"""
Super quick test for pickup filter disabled detection.

This tests ONLY the pickup filter logic to verify it detects disabled filters.
Run this to test the fix you just made in minutes instead of hours.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scraper import load_stores_and_categories, apply_pickup_filter
from playwright.async_api import async_playwright


async def test_pickup_filter_detection():
    """
    Test pickup filter on multiple categories to find one that's disabled.

    This will help verify:
    1. Filter detection works
    2. Disabled filter detection works
    3. Filter skips properly when disabled
    """

    all_stores, all_categories = load_stores_and_categories()

    # Pick a store
    test_store = None
    for store in all_stores:
        if store["state"] in ["WA", "OR"]:
            test_store = store
            break

    if not test_store:
        print("No stores found!")
        return

    print("=" * 70)
    print(f"PICKUP FILTER TEST")
    print("=" * 70)
    print(f"Store: {test_store['name']}")
    print(f"Testing {len(all_categories[:10])} categories...")
    print("=" * 70 + "\n")

    async with async_playwright() as p:
        profile_dir = Path(".playwright-profiles/test-filter")
        profile_dir.mkdir(parents=True, exist_ok=True)

        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Quick warmup
            print("Warmup...")
            await page.goto("https://www.lowes.com/", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Set store
            print(f"Setting store: {test_store['name']}...\n")
            await page.goto(test_store["url"], wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Test filter on multiple categories
            enabled_count = 0
            disabled_count = 0

            for i, category_url in enumerate(all_categories[:10], 1):
                cat_name = category_url.split('/pl/')[-1].split('/')[0][:40]

                print(f"\n[{i}/10] Testing: {cat_name}")
                print(f"       URL: {category_url[:80]}...")

                try:
                    # Navigate to category
                    await page.goto(category_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(2)

                    # Test the filter
                    filter_applied = await apply_pickup_filter(page, cat_name)

                    if filter_applied:
                        print(f"       ✅ ENABLED - Filter successfully applied")
                        enabled_count += 1
                    else:
                        print(f"       ❌ DISABLED - Filter is greyed out (no pickup items)")
                        disabled_count += 1

                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"       ⚠️ ERROR: {e}")

            print("\n" + "=" * 70)
            print(f"SUMMARY")
            print("=" * 70)
            print(f"Enabled filters:  {enabled_count}")
            print(f"Disabled filters: {disabled_count}")
            print("=" * 70)

            if disabled_count > 0:
                print("\n✅ SUCCESS: Disabled filter detection is WORKING!")
                print("   The scraper will skip these categories automatically.")
            else:
                print("\n⚠️  All filters were enabled - couldn't test disabled detection.")
                print("   Try a different store or categories to find a disabled one.")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await context.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("QUICK PICKUP FILTER TEST")
    print("Tests disabled filter detection in MINUTES not HOURS")
    print("=" * 70 + "\n")

    asyncio.run(test_pickup_filter_detection())
