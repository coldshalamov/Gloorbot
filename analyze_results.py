"""
Analyze scraping results for duplicates and bad URLs
Usage: python analyze_results.py
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_products():
    """Analyze scraped products"""
    output_file = Path("scrape_output/products.jsonl")

    if not output_file.exists():
        print("No results found at scrape_output/products.jsonl")
        return

    # Load products
    products = []
    with open(output_file) as f:
        for line in f:
            products.append(json.loads(line))

    print(f"\n{'='*70}")
    print(f"SCRAPING RESULTS ANALYSIS")
    print(f"{'='*70}")
    print(f"Total products scraped: {len(products)}")

    # Group by store
    by_store = defaultdict(list)
    for p in products:
        by_store[p['store_name']].append(p)

    print(f"\nProducts by store:")
    for store, prods in sorted(by_store.items()):
        print(f"  {store}: {len(prods)} products")

    # Check for duplicates (same URL across different stores)
    url_to_products = defaultdict(list)
    for p in products:
        url_to_products[p['url']].append(p)

    duplicates = {url: prods for url, prods in url_to_products.items() if len(prods) > 1}
    if duplicates:
        print(f"\nDuplicate products (same URL, different stores): {len(duplicates)}")
        print("  (This is expected - same product at different stores)")

    # Unique products
    unique_urls = len(url_to_products)
    print(f"\nUnique products (distinct URLs): {unique_urls}")

    # Products with markdowns
    with_markdown = [p for p in products if p.get('has_markdown')]
    print(f"Products with markdowns: {len(with_markdown)} ({len(with_markdown)/len(products)*100:.1f}%)")

    # Category coverage
    categories = set(p.get('category', 'Unknown') for p in products)
    print(f"\nCategories scraped: {len(categories)}")

    # Export summary
    summary = {
        "total_products": len(products),
        "unique_products": unique_urls,
        "stores_scraped": len(by_store),
        "categories_scraped": len(categories),
        "products_with_markdowns": len(with_markdown),
        "markdown_percentage": len(with_markdown)/len(products)*100 if products else 0
    }

    with open("scrape_output/summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to scrape_output/summary.json")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    analyze_products()
