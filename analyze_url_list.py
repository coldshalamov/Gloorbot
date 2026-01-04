"""
Analyze the URL list to identify parent categories vs leaf categories
Parent categories typically don't have product listings
"""

# Read the URLs
with open('apps/coordinator/data/urls.txt', 'r') as f:
    lines = f.readlines()

# Filter to only /pl/ URLs (category URLs)
category_urls = [line.strip() for line in lines if '/pl/' in line and line.strip().startswith('http')]

print(f"📊 Total category URLs: {len(category_urls)}\n")

# Analyze URL structure
# Parent categories often have patterns like:
# - /pl/Category-Name/ID (2 parts after /pl/)
# - Leaf categories: /pl/Specific-Item-Parent-Category/ID (3+ parts)

parent_like = []
leaf_like = []
unclear = []

for url in category_urls:
    # Extract the path after /pl/
    if '/pl/' in url:
        parts = url.split('/pl/')[1]
        # Count the segments (separated by /)
        segments = [p for p in parts.split('/') if p]
        
        # Heuristic: 
        # - 1 segment = likely parent (e.g., /pl/4294857979)
        # - 2 segments = could be either (e.g., /pl/Lighting-ceiling-fans/4294857979)
        # - 3+ segments = likely leaf (e.g., /pl/Pendant-lights-Lighting-ceiling-fans/4294857979)
        
        if len(segments) == 1:
            parent_like.append(url)
        elif len(segments) == 2:
            # Check if first segment is generic (short, no hyphens = just ID)
            first_seg = segments[0]
            if first_seg.isdigit() or len(first_seg) < 10:
                parent_like.append(url)
            else:
                # Has descriptive name, likely a category
                unclear.append(url)
        else:
            leaf_like.append(url)

print(f"🔴 Likely PARENT categories (no products): {len(parent_like)}")
if parent_like:
    print("   Examples:")
    for url in parent_like[:5]:
        print(f"   - {url}")

print(f"\n🟡 UNCLEAR (need manual review): {len(unclear)}")
if unclear:
    print("   Examples:")
    for url in unclear[:5]:
        print(f"   - {url}")

print(f"\n🟢 Likely LEAF categories (have products): {len(leaf_like)}")
if leaf_like:
    print("   Examples:")
    for url in leaf_like[:5]:
        print(f"   - {url}")

# Check for specific patterns that indicate parent categories
print("\n\n🔍 Checking for known parent category patterns...")

# Common parent categories that don't have products
parent_keywords = [
    'Appliances',
    'Building-supplies',
    'Tools',
    'Hardware',
    'Lighting-ceiling-fans',
    'Outdoor-living',
    'Paint',
    'Flooring',
    'Kitchen',
    'Bathroom',
    'Automotive',  # This is a parent!
    'Sports-fitness',
    'Outdoor-recreation',
    'Home-decor',
    'Accessible-home',
]

potential_parents = []
for url in category_urls:
    for keyword in parent_keywords:
        # Check if URL ends with keyword/ID pattern (parent category)
        if f'/{keyword}/' in url:
            # Check if it's JUST keyword/ID (parent) vs Subcategory-keyword/ID (leaf)
            parts_after_pl = url.split('/pl/')[1].split('/')
            if len(parts_after_pl) == 2 and parts_after_pl[0] == keyword:
                potential_parents.append(url)
                break

print(f"Found {len(potential_parents)} URLs matching parent category patterns:")
for url in potential_parents[:10]:
    print(f"   - {url}")

# Summary
print(f"\n\n📋 SUMMARY:")
print(f"   Total category URLs: {len(category_urls)}")
print(f"   Likely parents (no products): {len(parent_like)}")
print(f"   Pattern-matched parents: {len(potential_parents)}")
print(f"   Unclear: {len(unclear)}")
print(f"   Likely leaves (have products): {len(leaf_like)}")
print(f"\n⚠️  Estimated URLs that may need removal: {len(parent_like) + len(potential_parents)}")
