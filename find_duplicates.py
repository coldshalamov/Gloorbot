"""
Analyze url_audit_complete.json to find duplicate URLs
(URLs that show the same products)
"""

import json
from pathlib import Path
from collections import defaultdict

def find_duplicates():
    """Find URLs that show identical product sets"""
    audit_file = Path("url_audit_complete.json")

    if not audit_file.exists():
        print("Run audit_all_urls.py first!")
        return

    with open(audit_file) as f:
        results = json.load(f)

    print(f"Analyzing {len(results)} URLs for duplicates...")

    # Group by product ID sets
    product_set_to_urls = defaultdict(list)

    for result in results:
        if result.get('blocked') or 'error' in result:
            continue

        product_ids = tuple(sorted(result.get('product_ids', [])))
        if product_ids:  # Skip empty
            product_set_to_urls[product_ids].append(result['url'])

    # Find duplicate groups (same products)
    duplicate_groups = []
    for product_ids, urls in product_set_to_urls.items():
        if len(urls) > 1:
            duplicate_groups.append({
                "urls": urls,
                "product_count": len(product_ids),
                "sample_ids": list(product_ids[:5])
            })

    print(f"\nFound {len(duplicate_groups)} duplicate groups")

    # Save
    with open("DUPLICATE_URL_GROUPS.json", 'w') as f:
        json.dump(duplicate_groups, f, indent=2)

    # Print summary
    print(f"\nDuplicate groups saved to DUPLICATE_URL_GROUPS.json")
    print(f"\nTop 10 duplicate groups:")
    for i, group in enumerate(sorted(duplicate_groups, key=lambda g: len(g['urls']), reverse=True)[:10], 1):
        print(f"\n{i}. {len(group['urls'])} URLs show same {group['product_count']} products:")
        for url in group['urls']:
            print(f"   - {url}")

    # Find bad URLs (0 products)
    bad_urls = [r['url'] for r in results if r.get('count', 0) == 0 and not r.get('blocked')]

    with open("BAD_URLS.txt", 'w') as f:
        for url in bad_urls:
            f.write(url + '\n')

    print(f"\n{len(bad_urls)} URLs with 0 products saved to BAD_URLS.txt")

    # Create minimal set
    used_product_sets = set()
    minimal_urls = []

    for result in results:
        if result.get('blocked') or 'error' in result or result.get('count', 0) == 0:
            continue

        product_ids = tuple(sorted(result.get('product_ids', [])))
        if product_ids not in used_product_sets:
            used_product_sets.add(product_ids)
            minimal_urls.append(result['url'])

    with open("MINIMAL_URLS_DEDUPED.txt", 'w') as f:
        for url in minimal_urls:
            f.write(url + '\n')

    print(f"\n{len(minimal_urls)} unique URLs saved to MINIMAL_URLS_DEDUPED.txt")
    print(f"Reduced from {len(results)} to {len(minimal_urls)} ({len(results) - len(minimal_urls)} removed)")

if __name__ == "__main__":
    find_duplicates()
