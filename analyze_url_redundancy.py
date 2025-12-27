"""
URL Redundancy Analyzer

Analyzes scraped data to identify:
1. Redundant URLs (different URLs, same products)
2. Empty URLs (0 products)
3. Low-value URLs (<10 products)
4. Optimal URL set for maximum coverage with minimum scraping

Usage:
    python analyze_url_redundancy.py scrape_output/products.jsonl
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def analyze_redundancy(jsonl_file):
    """Analyze URL redundancy in scraped data"""

    print("="*70)
    print("URL REDUNDANCY ANALYSIS")
    print("="*70)

    # Load all products
    products = []
    with open(jsonl_file) as f:
        for line in f:
            products.append(json.loads(line))

    print(f"\nTotal products loaded: {len(products)}")

    # Group by URL (category)
    url_to_products = defaultdict(list)
    for p in products:
        # Extract category from product URL
        product_url = p.get('url', '')
        # Get the category this product came from (not in current data - need to add)
        # For now, we'll use a different approach

    # Group by product URL (actual product)
    product_urls = defaultdict(list)
    for p in products:
        product_urls[p.get('url', '')].append(p)

    print(f"Unique product URLs: {len(product_urls)}")

    # Analyze which category URLs produced which products
    # This requires the scraper to record the source category URL
    # Let's check if we have that data

    if 'category_url' not in products[0]:
        print("\n⚠️  WARNING: Products don't have 'category_url' field!")
        print("   The scraper needs to be updated to track source category.")
        print("   Cannot perform full redundancy analysis without this data.\n")
        print("SOLUTION: Update main.py to add 'category_url' to each product:")
        print("  Line ~220-230: Add this field:")
        print("    'category_url': category_url,")
        return

    # Group products by category URL
    category_to_products = defaultdict(set)
    for p in products:
        cat_url = p.get('category_url', 'unknown')
        product_url = p.get('url', '')
        category_to_products[cat_url].add(product_url)

    print(f"\nCategories analyzed: {len(category_to_products)}")

    # Find redundant categories
    print("\n" + "="*70)
    print("REDUNDANCY ANALYSIS")
    print("="*70)

    # Convert sets to frozensets for comparison
    category_products = {
        cat: frozenset(prods)
        for cat, prods in category_to_products.items()
    }

    redundant_groups = []
    checked = set()

    for cat1, prods1 in category_products.items():
        if cat1 in checked:
            continue

        # Find categories with identical product sets
        identical = []
        for cat2, prods2 in category_products.items():
            if cat1 != cat2 and prods1 == prods2:
                identical.append(cat2)
                checked.add(cat2)

        if identical:
            redundant_groups.append({
                'master': cat1,
                'duplicates': identical,
                'product_count': len(prods1)
            })
            checked.add(cat1)

    if redundant_groups:
        print(f"\n✅ Found {len(redundant_groups)} redundant category groups:")
        for i, group in enumerate(redundant_groups, 1):
            print(f"\nGroup {i}: {group['product_count']} identical products")
            print(f"  Master: {group['master']}")
            print(f"  Redundant URLs ({len(group['duplicates'])}):")
            for dup in group['duplicates']:
                print(f"    - {dup}")
    else:
        print("\n✅ No exact duplicate categories found")

    # Find subset relationships (category A contains all products from category B)
    print("\n" + "="*70)
    print("SUBSET ANALYSIS")
    print("="*70)

    subsets = []
    for cat1, prods1 in category_products.items():
        for cat2, prods2 in category_products.items():
            if cat1 != cat2:
                if prods2.issubset(prods1) and prods2 != prods1:
                    subsets.append({
                        'superset': cat1,
                        'superset_count': len(prods1),
                        'subset': cat2,
                        'subset_count': len(prods2),
                        'redundant_count': len(prods2)
                    })

    if subsets:
        print(f"\n✅ Found {len(subsets)} subset relationships:")
        for subset in subsets[:10]:  # Show first 10
            print(f"\n{subset['subset']}")
            print(f"  ({subset['subset_count']} products)")
            print(f"  is COMPLETELY CONTAINED IN:")
            print(f"  {subset['superset']}")
            print(f"  ({subset['superset_count']} products)")
            print(f"  → Can remove subset URL, use superset instead")
    else:
        print("\n✅ No subset relationships found")

    # Find low-value categories
    print("\n" + "="*70)
    print("LOW-VALUE CATEGORIES")
    print("="*70)

    low_value = []
    for cat, prods in category_to_products.items():
        if len(prods) < 10:
            low_value.append((cat, len(prods)))

    if low_value:
        low_value.sort(key=lambda x: x[1])
        print(f"\n✅ Found {len(low_value)} categories with <10 products:")
        for cat, count in low_value[:20]:  # Show first 20
            print(f"  {count:3d} products: {cat}")
    else:
        print("\n✅ All categories have ≥10 products")

    # Generate optimization recommendations
    print("\n" + "="*70)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("="*70)

    urls_to_remove = set()

    # Add exact duplicates
    for group in redundant_groups:
        urls_to_remove.update(group['duplicates'])

    # Add subsets
    for subset in subsets:
        urls_to_remove.add(subset['subset'])

    # Add low-value categories (optionally)
    # for cat, count in low_value:
    #     if count < 5:  # Very low value
    #         urls_to_remove.add(cat)

    if urls_to_remove:
        print(f"\n✅ Recommended URLs to REMOVE: {len(urls_to_remove)}")
        print("\nSaving to URLS_TO_REMOVE.txt...")

        with open('URLS_TO_REMOVE.txt', 'w') as f:
            f.write("# URLs to Remove from LowesMap.txt\n")
            f.write("# These are redundant/low-value categories\n\n")

            f.write("## Exact Duplicates\n")
            for group in redundant_groups:
                f.write(f"\n# Group with {group['product_count']} products:\n")
                f.write(f"# Keep: {group['master']}\n")
                for dup in group['duplicates']:
                    f.write(f"{dup}\n")

            f.write("\n## Subsets (contained in larger categories)\n")
            for subset in subsets:
                f.write(f"\n# {subset['subset_count']} products, contained in {subset['superset']}\n")
                f.write(f"{subset['subset']}\n")

        print(f"✅ Saved to URLS_TO_REMOVE.txt")

    # Calculate optimized coverage
    all_products_from_removed = set()
    for cat in urls_to_remove:
        all_products_from_removed.update(category_to_products.get(cat, set()))

    remaining_categories = set(category_to_products.keys()) - urls_to_remove
    all_products_from_remaining = set()
    for cat in remaining_categories:
        all_products_from_remaining.update(category_to_products.get(cat, set()))

    coverage_loss = len(all_products_from_removed - all_products_from_remaining)

    print(f"\n📊 OPTIMIZATION SUMMARY:")
    print(f"  Original categories: {len(category_to_products)}")
    print(f"  Recommended to remove: {len(urls_to_remove)}")
    print(f"  Optimized count: {len(remaining_categories)}")
    print(f"  Products in removed URLs: {len(all_products_from_removed)}")
    print(f"  Coverage loss: {coverage_loss} products ({coverage_loss/len(product_urls)*100:.1f}%)")

    if coverage_loss == 0:
        print("\n🎉 PERFECT! Can remove URLs with ZERO coverage loss!")
    elif coverage_loss < len(product_urls) * 0.01:
        print("\n✅ EXCELLENT! <1% coverage loss")
    else:
        print("\n⚠️  Moderate coverage loss - review carefully")

    print("\n" + "="*70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_url_redundancy.py scrape_output/products.jsonl")
        sys.exit(1)

    jsonl_file = sys.argv[1]
    if not Path(jsonl_file).exists():
        print(f"❌ File not found: {jsonl_file}")
        sys.exit(1)

    analyze_redundancy(jsonl_file)
