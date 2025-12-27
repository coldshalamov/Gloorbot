"""
Analyze actual product overlap between categories to determine optimal category set.

This script will:
1. Scrape a small sample from each category
2. Track which products appear in multiple categories
3. Calculate actual duplication rates
4. Recommend optimal category subset
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict
import json

sys.path.insert(0, str(Path(__file__).parent / "apify_actor_seed" / "src"))

from main import (
    load_stores_and_categories,
    warmup_session,
    set_store_context,
    scrape_category_page
)
from playwright.async_api import async_playwright


async def sample_category(page, category_url, store_info, max_pages=2):
    """Scrape first 2 pages of a category to get product sample"""
    products = []

    for page_num in range(1, max_pages + 1):
        try:
            page_products = await asyncio.wait_for(
                scrape_category_page(page, category_url, store_info, page_num),
                timeout=120.0
            )

            if not page_products:
                break

            products.extend(page_products)

            if len(page_products) < 12:
                break

        except Exception as e:
            print(f"Error sampling {category_url}: {e}")
            break

    return products


async def analyze_overlap():
    """Main analysis function"""

    # Load both category sets
    current_cats = set(line.strip() for line in open('LowesMap.txt')
                      if line.startswith('https://www.lowes.com/pl/'))
    pruned_cats = set(line.strip() for line in open('LowesMap_Final_Pruned.txt')
                     if line.startswith('https://www.lowes.com/pl/'))

    # Use first store for testing
    all_stores, _ = load_stores_and_categories()
    wa_stores = [s for s in all_stores if s["state"] == "WA"]
    test_store = wa_stores[0]

    print(f"Testing with store: {test_store['name']}")
    print(f"Current categories: {len(current_cats)}")
    print(f"Pruned categories: {len(pruned_cats)}")
    print(f"Union: {len(current_cats | pruned_cats)}")
    print()

    # Sample categories
    category_products = {}  # category_url -> set of product URLs
    product_categories = defaultdict(set)  # product_url -> set of categories it appears in

    all_categories = list(current_cats | pruned_cats)

    async with async_playwright() as p:
        profile_dir = Path(f".playwright-profiles/overlap-test")
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
                "--disable-gpu",
                "--no-sandbox",
            ]
        }

        context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            print("Warming up browser...")
            await warmup_session(page)
            await set_store_context(page, test_store["url"], test_store["name"])

            # Sample first 50 categories to get representative data
            sample_size = min(50, len(all_categories))
            print(f"\nSampling {sample_size} categories (first 2 pages each)...")

            for idx, category_url in enumerate(all_categories[:sample_size]):
                cat_name = category_url.split('/pl/')[1].split('/')[0][:40]
                print(f"[{idx+1}/{sample_size}] Sampling: {cat_name}")

                products = await sample_category(page, category_url, test_store, max_pages=2)

                if products:
                    product_urls = set(p['url'] for p in products)
                    category_products[category_url] = product_urls

                    # Track which categories each product appears in
                    for prod_url in product_urls:
                        product_categories[prod_url].add(category_url)

                    print(f"    Found {len(products)} products")
                else:
                    print(f"    No products found")

                await asyncio.sleep(1)

        finally:
            await context.close()

    # Analysis
    print("\n" + "="*70)
    print("OVERLAP ANALYSIS")
    print("="*70)

    total_products = len(product_categories)
    products_in_multiple_cats = sum(1 for cats in product_categories.values() if len(cats) > 1)

    print(f"\nTotal unique products: {total_products}")
    print(f"Products in multiple categories: {products_in_multiple_cats} ({products_in_multiple_cats/total_products*100:.1f}%)")
    print(f"Products in single category: {total_products - products_in_multiple_cats} ({(total_products - products_in_multiple_cats)/total_products*100:.1f}%)")

    # Find products appearing in most categories
    print("\nProducts appearing in MOST categories:")
    sorted_products = sorted(product_categories.items(), key=lambda x: len(x[1]), reverse=True)
    for prod_url, cats in sorted_products[:5]:
        print(f"  {len(cats)} categories: {prod_url}")

    # Calculate duplication rate
    total_scraped_products = sum(len(prods) for prods in category_products.values())
    duplication_rate = (total_scraped_products - total_products) / total_scraped_products * 100

    print(f"\nDuplication analysis:")
    print(f"  Total products scraped (with duplicates): {total_scraped_products}")
    print(f"  Unique products: {total_products}")
    print(f"  Duplication rate: {duplication_rate:.1f}%")

    # Estimate for full scrape
    if duplication_rate > 0:
        current_unique = len(set(p for cat in current_cats if cat in category_products for p in category_products[cat]))
        pruned_unique = len(set(p for cat in pruned_cats if cat in category_products for p in category_products[cat]))
        union_unique = total_products

        print(f"\nEstimated unique products (based on sample):")
        print(f"  Current (515 cats): {current_unique} unique products")
        print(f"  Pruned (716 cats): {pruned_unique} unique products")
        print(f"  Union (815 cats): {union_unique} unique products")

        if current_unique > 0:
            pruned_gain = (pruned_unique - current_unique) / current_unique * 100
            union_gain = (union_unique - current_unique) / current_unique * 100

            print(f"\nGain over Current:")
            print(f"  Pruned: +{pruned_gain:.1f}% more unique products for +39% cost")
            print(f"  Union: +{union_gain:.1f}% more unique products for +58% cost")

            # Recommendation
            print("\n" + "="*70)
            print("RECOMMENDATION")
            print("="*70)

            if union_gain < 20:
                print("❌ Union (815 cats) is INEFFICIENT")
                print(f"   Only {union_gain:.1f}% more products for 58% more cost")
                print("   Lots of duplication - categories overlap heavily")
            elif union_gain > 40:
                print("✅ Union (815 cats) is EFFICIENT")
                print(f"   {union_gain:.1f}% more products for 58% more cost")
                print("   Minimal duplication - categories are mostly distinct")
            else:
                print("⚠️  Union (815 cats) is BORDERLINE")
                print(f"   {union_gain:.1f}% more products for 58% more cost")
                print("   Moderate duplication - curated subset might be better")

    # Save detailed results
    with open('category_overlap_analysis.json', 'w') as f:
        json.dump({
            'total_products': total_products,
            'products_in_multiple_categories': products_in_multiple_cats,
            'duplication_rate': duplication_rate,
            'category_products': {k: list(v) for k, v in category_products.items()},
            'product_categories': {k: list(v) for k, v in product_categories.items()}
        }, f, indent=2)

    print(f"\nDetailed results saved to: category_overlap_analysis.json")


if __name__ == "__main__":
    asyncio.run(analyze_overlap())
