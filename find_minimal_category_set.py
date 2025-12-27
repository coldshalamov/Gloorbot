"""
Intelligent category set optimizer.

Strategy:
1. Identify category hierarchy patterns (parent/child relationships)
2. Sample products from each category
3. Find minimum set of categories that covers all products
4. This is a Set Cover optimization problem

The goal: Find the smallest subset of categories that yields 99%+ unique products
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict
import json
import re

sys.path.insert(0, str(Path(__file__).parent / "apify_actor_seed" / "src"))

from main import (
    load_stores_and_categories,
    warmup_session,
    set_store_context,
    scrape_category_page
)
from playwright.async_api import async_playwright


def extract_category_name(category_url):
    """Extract category name from URL"""
    return category_url.split('/pl/')[1].split('/')[0]


def analyze_category_hierarchy(all_categories):
    """
    Identify potential parent-child relationships by analyzing category names.

    Examples:
    - "Lighting-ceiling-fans" is likely parent of "Ceiling-lights"
    - "Tools" is likely parent of "Hand-tools"
    """

    names = {cat: extract_category_name(cat) for cat in all_categories}

    # Find potential parents (shorter, more general names)
    potential_parents = {}
    potential_children = defaultdict(list)

    for cat_url, name in names.items():
        # Count hyphens as a proxy for specificity (more hyphens = more specific)
        specificity = name.count('-')
        potential_parents[cat_url] = specificity

    # Sort by specificity
    sorted_by_specificity = sorted(potential_parents.items(), key=lambda x: x[1])

    # Simple heuristic: if name A is substring of name B, A might be parent of B
    hierarchy = defaultdict(list)
    for cat_a, spec_a in sorted_by_specificity:
        name_a = names[cat_a]
        for cat_b, spec_b in sorted_by_specificity:
            if cat_a != cat_b and spec_a < spec_b:
                name_b = names[cat_b]
                # If name_a is contained in name_b, might be parent
                if name_a in name_b or name_b.startswith(name_a):
                    hierarchy[cat_a].append(cat_b)

    return hierarchy


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
            pass

    return products


async def find_minimal_set():
    """Main optimization function"""

    # Load category sets
    current_cats = set(line.strip() for line in open('LowesMap.txt')
                      if line.startswith('https://www.lowes.com/pl/'))
    pruned_cats = set(line.strip() for line in open('LowesMap_Final_Pruned.txt')
                     if line.startswith('https://www.lowes.com/pl/'))

    all_categories = sorted(list(current_cats | pruned_cats))

    print(f"Current: {len(current_cats)} categories")
    print(f"Pruned: {len(pruned_cats)} categories")
    print(f"Union: {len(all_categories)} categories")
    print()

    # Load test store
    all_stores, _ = load_stores_and_categories()
    wa_stores = [s for s in all_stores if s["state"] == "WA"]
    test_store = wa_stores[0]

    print(f"Testing with: {test_store['name']}")
    print()

    # Analyze hierarchy
    print("Analyzing category hierarchy...")
    hierarchy = analyze_category_hierarchy(all_categories)

    # Identify suspicious categories (promotional, brand-specific)
    suspicious_patterns = [
        'SHOP-', 'Shop-', 'New-and-Trending', 'December-deal', 'Deals',
        'Google--', 'Ecobee--', 'Klein-',  # Brand-specific
    ]

    suspicious_cats = set()
    for cat in all_categories:
        name = extract_category_name(cat)
        if any(pattern.lower() in name.lower() for pattern in suspicious_patterns):
            suspicious_cats.add(cat)

    print(f"Found {len(suspicious_cats)} suspicious categories (promotional/brand pages)")
    print()

    # Sample categories strategically
    category_products = {}
    product_categories = defaultdict(set)

    # Sample all categories but prioritize non-suspicious ones first
    sample_order = sorted([c for c in all_categories if c not in suspicious_cats]) + \
                   sorted(suspicious_cats)

    # Sample first 80 categories
    sample_size = min(80, len(sample_order))
    print(f"Sampling {sample_size} categories (first 2 pages each)...")

    async with async_playwright() as p:
        profile_dir = Path(f".playwright-profiles/minimal-set-test")
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
            await asyncio.sleep(2)

            for idx, category_url in enumerate(sample_order[:sample_size]):
                cat_name = extract_category_name(category_url)[:40]
                is_suspicious = category_url in suspicious_cats
                marker = " [SUSPICIOUS]" if is_suspicious else ""

                print(f"[{idx+1:2d}/{sample_size}] {cat_name}{marker}")

                try:
                    products = await sample_category(page, category_url, test_store, max_pages=2)

                    if products:
                        product_urls = set(p['url'] for p in products)
                        category_products[category_url] = product_urls

                        # Track which categories each product appears in
                        for prod_url in product_urls:
                            product_categories[prod_url].add(category_url)

                        print(f"           {len(products)} products")

                except Exception as e:
                    print(f"           ERROR: {e}")

                await asyncio.sleep(0.5)

        finally:
            await context.close()

    print()
    print("=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)

    # Calculate metrics
    total_unique_products = len(product_categories)
    products_in_multiple = sum(1 for cats in product_categories.values() if len(cats) > 1)

    print(f"\nTotal unique products found: {total_unique_products}")
    print(f"Products in multiple categories: {products_in_multiple} ({products_in_multiple/total_unique_products*100:.1f}%)")

    # Products per category
    avg_products_per_category = sum(len(prods) for prods in category_products.values()) / len(category_products) if category_products else 0
    print(f"Average products per category: {avg_products_per_category:.0f}")

    # Find most "valuable" categories (cover most unique products)
    print("\nMost valuable categories (cover most unique products):")
    category_value = {}
    for cat_url, prod_urls in category_products.items():
        # Value = number of products only in this category + contribution to multi-category products
        unique_only = sum(1 for purl in prod_urls if len(product_categories[purl]) == 1)
        category_value[cat_url] = len(prod_urls)

    top_categories = sorted(category_value.items(), key=lambda x: x[1], reverse=True)[:15]
    for cat_url, value in top_categories:
        name = extract_category_name(cat_url)
        is_sus = "[SUSPICIOUS]" if cat_url in suspicious_cats else ""
        print(f"  {value:3d} products: {name} {is_sus}")

    # Find minimum set using greedy algorithm
    print("\n" + "=" * 70)
    print("FINDING MINIMAL CATEGORY SET (Greedy Set Cover)")
    print("=" * 70)

    covered_products = set()
    selected_categories = []
    remaining_categories = set(category_products.keys())

    while covered_products != set(category_products.keys()):
        # Find category that covers the most uncovered products
        best_cat = None
        best_coverage = 0

        for cat_url in remaining_categories:
            uncovered = len(category_products[cat_url] - covered_products)
            if uncovered > best_coverage:
                best_coverage = uncovered
                best_cat = cat_url

        if best_cat is None:
            break

        selected_categories.append(best_cat)
        covered_products.update(category_products[best_cat])
        remaining_categories.remove(best_cat)

        # Stop after covering 99% of products
        coverage_percent = len(covered_products) / total_unique_products * 100
        if coverage_percent >= 99:
            print(f"\n✓ Reached 99% coverage ({len(covered_products)} / {total_unique_products} products)")
            break

    print(f"\nMinimal set size: {len(selected_categories)} categories")
    print(f"Coverage: {len(covered_products)} / {total_unique_products} products ({len(covered_products)/total_unique_products*100:.1f}%)")

    # Analyze the selected set
    current_in_minimal = len([c for c in selected_categories if c in current_cats])
    pruned_in_minimal = len([c for c in selected_categories if c in pruned_cats])
    suspicious_in_minimal = len([c for c in selected_categories if c in suspicious_cats])

    print(f"\nSelected categories composition:")
    print(f"  From Current (515): {current_in_minimal}")
    print(f"  From Pruned (716): {pruned_in_minimal}")
    print(f"  Suspicious categories: {suspicious_in_minimal}")

    # Estimate for full scrape
    print("\n" + "=" * 70)
    print("EXTRAPOLATION TO FULL CATALOG")
    print("=" * 70)

    # Estimate duplication rate
    total_scraped = sum(len(prods) for prods in category_products.values())
    duplication_rate = (total_scraped - total_unique_products) / total_scraped * 100 if total_scraped > 0 else 0

    print(f"\nBased on {sample_size} categories sampled:")
    print(f"  Duplication rate: {duplication_rate:.1f}%")

    # Estimate unique products with different category sets
    current_coverage = len([c for c in current_cats if c in category_products])
    pruned_coverage = len([c for c in pruned_cats if c in category_products])

    if current_coverage > 0:
        current_unique_pct = len([c for c in current_cats if c in selected_categories]) / current_coverage * 100
        print(f"  Current (515 cats): {current_unique_pct:.0f}% need to be included in minimal set")

    # Final recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)

    print(f"\nUse {len(selected_categories)} categories for minimal complete coverage:")
    print(f"  - From Current (515): {current_in_minimal} categories")
    print(f"  - From Pruned (716): {pruned_in_minimal} categories")
    print(f"  - Total: {len(selected_categories)} categories")
    print(f"\nThis covers {len(covered_products)} unique products (99%+ of sampled catalog)")
    print(f"Avoid {suspicious_in_minimal} suspicious/promotional categories")

    # Save detailed results
    results = {
        'sample_size': sample_size,
        'total_unique_products': total_unique_products,
        'products_in_multiple_categories': products_in_multiple,
        'duplication_rate': duplication_rate,
        'minimal_set_size': len(selected_categories),
        'minimal_set_coverage': len(covered_products) / total_unique_products * 100,
        'suspicious_categories_count': len(suspicious_cats),
        'selected_categories': [extract_category_name(c) for c in selected_categories],
        'suspicious_categories': [extract_category_name(c) for c in suspicious_cats if c in category_products],
        'recommendation': {
            'minimal_categories': len(selected_categories),
            'from_current': current_in_minimal,
            'from_pruned': pruned_in_minimal,
            'suspicious_to_exclude': suspicious_in_minimal
        }
    }

    with open('minimal_category_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: minimal_category_analysis.json")


if __name__ == "__main__":
    asyncio.run(find_minimal_set())
