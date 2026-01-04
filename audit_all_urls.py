"""
Comprehensive URL audit - check all URL sources and identify problematic patterns
"""

print("="*70)
print("COMPREHENSIVE URL AUDIT")
print("="*70)

# Check all URL files
url_files = [
    "apps/coordinator/data/urls.txt",
    "PARALLEL/urls.txt",
    "LowesMap.txt",
    "new_categories.txt",
]

for filepath in url_files:
    try:
        with open(filepath, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
        
        # Filter to actual URLs
        urls = [l for l in lines if l and l.startswith('http')]
        
        # Count different types
        c_urls = [u for u in urls if '/c/' in u]
        pl_urls = [u for u in urls if '/pl/' in u]
        store_urls = [u for u in urls if '/store/' in u]
        
        print(f"\n📄 {filepath}")
        print(f"   Total lines: {len(lines)}")
        print(f"   Total URLs: {len(urls)}")
        print(f"   Store URLs: {len(store_urls)}")
        print(f"   /pl/ URLs (product listings): {len(pl_urls)}")
        print(f"   /c/ URLs (category pages): {len(c_urls)}")
        
        if c_urls:
            print(f"\n   🔴 FOUND /c/ URLs (these will loop forever):")
            for url in c_urls[:10]:
                print(f"      - {url}")
            if len(c_urls) > 10:
                print(f"      ... and {len(c_urls) - 10} more")
    
    except FileNotFoundError:
        print(f"\n📄 {filepath} - NOT FOUND")
    except Exception as e:
        print(f"\n📄 {filepath} - ERROR: {e}")

# Check for parent category patterns
print("\n\n" + "="*70)
print("CHECKING FOR PARENT CATEGORY PATTERNS")
print("="*70)

try:
    with open("apps/coordinator/data/urls.txt", 'r') as f:
        urls = [l.strip() for l in f.readlines() if l.strip().startswith('http') and '/pl/' in l]
    
    # Analyze URL structure
    parent_like = []
    leaf_like = []
    
    for url in urls:
        if '/pl/' in url:
            # Extract path after /pl/
            parts = url.split('/pl/')[1].split('/')
            segments = [p for p in parts if p and not p.isdigit()]
            
            # Parent categories typically have 0-1 descriptive segments
            # Leaf categories have 2+ descriptive segments
            if len(segments) <= 1:
                parent_like.append(url)
            else:
                leaf_like.append(url)
    
    print(f"\n🟡 Possible parent categories (may have no products): {len(parent_like)}")
    if parent_like:
        print("   Examples:")
        for url in parent_like[:10]:
            print(f"   - {url}")
    
    print(f"\n🟢 Likely leaf categories (should have products): {len(leaf_like)}")
    
except Exception as e:
    print(f"Error analyzing URL structure: {e}")

print("\n\n" + "="*70)
print("SUMMARY")
print("="*70)
print("\n✅ Good news: No /c/ URLs found in any file!")
print("\n⚠️  If you're seeing /c/ URLs in the running scraper:")
print("   1. Check if it's connecting to a REMOTE coordinator")
print("   2. Check the remote coordinator's database")
print("   3. The remote database may have old/bad URLs")
print("\n💡 To fix a remote coordinator:")
print("   1. SSH/access the remote server")
print("   2. Run: DELETE FROM tasks WHERE category_url LIKE '%/c/%';")
print("   3. Restart the coordinator")
