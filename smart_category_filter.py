"""
Smart category filtering without needing full browser sampling.

Uses statistical analysis and pattern recognition to determine:
1. Which categories are definitely redundant (promotional, brand pages)
2. Estimate overlap based on category name patterns
3. Recommend optimal subset

This approach is much faster and doesn't require extensive browser sampling.
"""

import re
from collections import defaultdict
from pathlib import Path


def extract_category_name(category_url):
    """Extract category name from URL"""
    return category_url.split('/pl/')[1].split('/')[0]


def categorize_by_pattern(category_url):
    """Classify categories by type"""
    name = extract_category_name(category_url)
    name_lower = name.lower()

    # Suspicious/promotional categories (definitely redundant)
    if any(pattern in name_lower for pattern in [
        'shop-', 'deal', 'trending', 'special-value', 'clearance'
    ]):
        return 'promotional'

    # Brand-specific categories (likely redundant with product categories)
    if any(pattern in name_lower for pattern in [
        'google--', 'ecobee--', 'klein-tools', 'dewalt', 'craftsman',
        'signature', 'kobalt', 'portfolio'
    ]):
        return 'brand_specific'

    # Likely parent categories (broader, might contain children)
    if any(word in name_lower for word in [
        'all-', 'various', 'miscellaneous', 'accessories', 'parts'
    ]):
        return 'parent'

    # Leaf/specific categories (most valuable)
    return 'leaf'


def analyze_url_structure(category_url):
    """Analyze URL structure to detect hierarchy"""
    # URL format: https://www.lowes.com/pl/Category-Name-Breadcrumb/ID
    parts = category_url.split('/')
    breadcrumb = parts[4] if len(parts) > 4 else ""

    # Breadcrumb shows hierarchy: "Category-Subcategory-Parent"
    breadcrumb_parts = breadcrumb.split('-')

    return {
        'url': category_url,
        'name': extract_category_name(category_url),
        'breadcrumb_depth': len([p for p in breadcrumb_parts if p and not p.isdigit()]),
        'breadcrumb': breadcrumb
    }


def find_smart_category_subset():
    """
    Determine optimal category subset using intelligent filtering
    """

    # Load category sets
    current_cats = set(line.strip() for line in open('LowesMap.txt')
                      if line.startswith('https://www.lowes.com/pl/'))
    pruned_cats = set(line.strip() for line in open('LowesMap_Final_Pruned.txt')
                     if line.startswith('https://www.lowes.com/pl/'))

    all_categories = sorted(list(current_cats | pruned_cats))

    print("=" * 70)
    print("INTELLIGENT CATEGORY FILTERING")
    print("=" * 70)

    print(f"\nStarting inventory:")
    print(f"  Current (LowesMap.txt): {len(current_cats)} categories")
    print(f"  Pruned (LowesMap_Final_Pruned.txt): {len(pruned_cats)} categories")
    print(f"  Overlap: {len(current_cats & pruned_cats)} categories")
    print(f"  Union: {len(all_categories)} categories")

    # Classify all categories
    categories_by_type = defaultdict(list)
    suspicious_cats = []
    leaf_cats = []
    parent_cats = []

    for cat in all_categories:
        cat_type = categorize_by_pattern(cat)
        categories_by_type[cat_type].append(cat)

        if cat_type in ['promotional', 'brand_specific']:
            suspicious_cats.append(cat)
        elif cat_type == 'leaf':
            leaf_cats.append(cat)
        elif cat_type == 'parent':
            parent_cats.append(cat)

    print(f"\nCategory breakdown:")
    print(f"  Leaf/Specific categories: {len(leaf_cats)}")
    print(f"  Parent categories: {len(parent_cats)}")
    print(f"  Promotional (REDUNDANT): {len(categories_by_type['promotional'])}")
    print(f"  Brand-specific (LIKELY REDUNDANT): {len(categories_by_type['brand_specific'])}")

    # Analyze coverage
    print(f"\nRedundancy analysis:")
    print(f"  Suspicious categories found: {len(suspicious_cats)}")
    print(f"  If excluded, remaining: {len(all_categories) - len(suspicious_cats)} categories")
    print(f"  Potential cost reduction: {len(suspicious_cats)/len(all_categories)*100:.1f}%")

    # Check for obvious overlaps
    print(f"\nOverlap analysis:")

    # Find categories that appear in both Current and Pruned
    overlap_cats = current_cats & pruned_cats
    only_current = current_cats - pruned_cats
    only_pruned = pruned_cats - current_cats

    print(f"  In both files: {len(overlap_cats)} categories")
    print(f"  Only in Current: {len(only_current)} categories")
    print(f"  Only in Pruned: {len(only_pruned)} categories")

    # Analyze what Current is missing from Pruned
    print(f"\nCoverage analysis:")
    print(f"  Current file covers: {len(overlap_cats)/len(only_pruned)*100:.1f}% of Pruned's unique categories")

    missing_from_current = only_pruned - set(suspicious_cats)
    print(f"  Non-suspicious categories missing from Current: {len(missing_from_current)}")

    # Estimate from known patterns
    print(f"\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    recommended_categories = set()

    # 1. Keep all leaf categories (most specific, least likely to overlap)
    recommended_categories.update(leaf_cats)

    # 2. Keep parent categories if they have unique content
    recommended_categories.update(parent_cats)

    # 3. Exclude all promotional categories
    print(f"\n1. Exclude promotional categories:")
    print(f"   - {len(categories_by_type['promotional'])} categories like:")
    for cat in categories_by_type['promotional'][:5]:
        print(f"     - {extract_category_name(cat)}")

    # 4. Consider brand-specific pages
    print(f"\n2. Review brand-specific categories:")
    print(f"   - {len(categories_by_type['brand_specific'])} brand pages found")
    print(f"   - These often duplicate products from regular categories")

    # Don't exclude brand pages yet, just note them
    recommended_categories.update(categories_by_type['brand_specific'])

    # Final recommendation
    optimized_set = recommended_categories - set(categories_by_type['promotional'])

    print(f"\n" + "-" * 70)
    print("PROPOSED OPTIMIZED SET")
    print("-" * 70)

    print(f"\nOptimized category set:")
    print(f"  Total categories: {len(optimized_set)}")
    print(f"  Original union: {len(all_categories)}")
    print(f"  Reduction: {(1 - len(optimized_set)/len(all_categories))*100:.1f}%")

    # Breakdown by source
    optimized_from_current = len([c for c in optimized_set if c in current_cats])
    optimized_from_pruned = len([c for c in optimized_set if c in pruned_cats])

    print(f"\nComposition:")
    print(f"  From Current (515): {optimized_from_current} categories")
    print(f"  From Pruned (716): {optimized_from_pruned} categories")

    # Estimate cost
    print(f"\nEstimated cost comparison:")
    print(f"  Current (515 cats): BASELINE")
    print(f"  Pruned (716 cats): +{(716-515)/515*100:.0f}% more page loads")
    print(f"  Optimized ({len(optimized_set)} cats): +{(len(optimized_set)-515)/515*100:.0f}% more page loads")
    print(f"  Union (815 cats): +{(815-515)/515*100:.0f}% more page loads")

    # Second phase: even more aggressive (exclude brand pages)
    aggressive_set = optimized_set - set(categories_by_type['brand_specific'])

    print(f"\n" + "-" * 70)
    print("AGGRESSIVE OPTIMIZATION (exclude brand pages)")
    print("-" * 70)

    print(f"\nIf we exclude brand-specific pages:")
    print(f"  Categories: {len(aggressive_set)}")
    print(f"  Further reduction: {(1 - len(aggressive_set)/len(optimized_set))*100:.1f}%")
    print(f"  Cost vs Current: +{(len(aggressive_set)-515)/515*100:.0f}%")

    # Warnings
    print(f"\n" + "=" * 70)
    print("IMPORTANT NOTES")
    print("=" * 70)

    print(f"""
1. PROMOTIONAL EXCLUSION (high confidence):
   Removing ~{len(categories_by_type['promotional'])} promotional categories
   - "SHOP-*-DEALS" pages are definitely redundant
   - Products already in regular categories
   - Safe to exclude

2. BRAND PAGE EXCLUSION (medium confidence):
   Removing ~{len(categories_by_type['brand_specific'])} brand pages
   - "Google--*", "Ecobee--*", "Klein-tools" etc.
   - These products likely in regular categories
   - ~80% confident these are redundant
   - But 20% risk of missing brand-exclusive deals

3. COVERAGE UNKNOWN:
   Without full sampling, can't determine:
   - Whether parent categories contain child products
   - Exact duplication rate
   - If missing categories add unique products

   Recommendation: Use OPTIMIZED set (exclude promotional only)
   This gives us ~{(len(optimized_set)-515)/515*100:.0f}% more coverage
   while being conservative about exclusions
""")

    # Save recommendations
    results = {
        'analysis_type': 'smart_filtering',
        'current_categories': len(current_cats),
        'pruned_categories': len(pruned_cats),
        'union_categories': len(all_categories),
        'suspicious_promotional': len(categories_by_type['promotional']),
        'brand_specific': len(categories_by_type['brand_specific']),
        'leaf_categories': len(leaf_cats),
        'parent_categories': len(parent_cats),
        'recommended_set_size': len(optimized_set),
        'aggressive_set_size': len(aggressive_set),
        'cost_increase_optimized': f"+{(len(optimized_set)-515)/515*100:.0f}%",
        'cost_increase_aggressive': f"+{(len(aggressive_set)-515)/515*100:.0f}%",
        'cost_increase_union': f"+{(815-515)/515*100:.0f}%",
        'promotional_categories_to_exclude': [extract_category_name(c) for c in categories_by_type['promotional'][:20]],
        'brand_categories_to_review': [extract_category_name(c) for c in categories_by_type['brand_specific'][:20]]
    }

    import json
    with open('smart_category_recommendations.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Write actual category URLs to file
    with open('LowesMap_Recommended.txt', 'w') as f:
        f.write('# Recommended optimized category list\n')
        f.write('# Excludes promotional/deal pages\n')
        f.write('# Includes all leaf and parent categories\n\n')

        # Include stores first
        for line in open('LowesMap.txt'):
            if '/store/' in line:
                f.write(line)

        f.write('\n## RECOMMENDED CATEGORIES\n\n')
        for cat in sorted(optimized_set):
            f.write(cat + '\n')

    print(f"\n[+] Recommendations saved to: LowesMap_Recommended.txt")
    print(f"[+] Detailed results saved to: smart_category_recommendations.json")


if __name__ == "__main__":
    find_smart_category_subset()
