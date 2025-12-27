"""
Check the lpl-refinements sitemaps for category URLs
"""
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

def fetch_sitemap(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_urls(content):
    urls = []
    try:
        root = ET.fromstring(content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for url_elem in root.findall('.//ns:url', ns):
            loc = url_elem.find('ns:loc', ns)
            if loc is not None and loc.text:
                urls.append(loc.text)
        return urls
    except:
        return []

print("Checking lpl-refinements sitemaps...")
print("="*60)

all_category_urls = set()

for i in range(4):
    url = f"https://www.lowes.com/sitemap/lpl-refinements{i}.xml"
    print(f"\n[{i+1}/4] {url}")
    content = fetch_sitemap(url)
    if content:
        urls = parse_urls(content)
        pl_urls = [u for u in urls if '/pl/' in u]
        print(f"  Total URLs: {len(urls)}")
        print(f"  Category URLs (/pl/): {len(pl_urls)}")
        
        if pl_urls:
            all_category_urls.update(pl_urls)
            print(f"  Sample: {pl_urls[0]}")

print("\n" + "="*60)
print(f"TOTAL CATEGORY URLs FOUND: {len(all_category_urls)}")
print("="*60)

if all_category_urls:
    # Normalize URLs (remove query params)
    normalized = {url.split('?')[0].rstrip('/') for url in all_category_urls}
    
    # Load LowesMap.txt
    map_path = Path("LowesMap.txt")
    if map_path.exists():
        lowes_map_urls = set()
        with open(map_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '/pl/' in line:
                    base_url = line.split('?')[0].rstrip('/')
                    lowes_map_urls.add(base_url)
        
        print(f"\nLowesMap.txt has: {len(lowes_map_urls)} category URLs")
        print(f"Sitemap has: {len(normalized)} category URLs")
        
        common = lowes_map_urls & normalized
        missing_from_map = normalized - lowes_map_urls
        extra_in_map = lowes_map_urls - normalized
        
        print(f"\nCommon: {len(common)}")
        print(f"Missing from LowesMap.txt: {len(missing_from_map)}")
        print(f"Extra in LowesMap.txt: {len(extra_in_map)}")
        
        coverage_pct = (len(common) / len(normalized) * 100) if normalized else 0
        print(f"\n✅ Coverage: {coverage_pct:.1f}% of sitemap categories are in LowesMap.txt")
        
        if missing_from_map:
            print(f"\n⚠️  Missing from LowesMap.txt (first 20):")
            for url in sorted(list(missing_from_map))[:20]:
                print(f"  - {url}")
        
        if extra_in_map and len(extra_in_map) < 50:
            print(f"\n💡 Extra in LowesMap.txt (not in sitemap):")
            for url in sorted(list(extra_in_map)):
                print(f"  - {url}")
        elif extra_in_map:
            print(f"\n💡 {len(extra_in_map)} URLs in LowesMap.txt are not in sitemap")
            print("   (These might be deep subcategories or deprecated URLs)")
        
        # Save comparison
        import json
        comparison = {
            "sitemap_categories": len(normalized),
            "lowesmap_categories": len(lowes_map_urls),
            "common": len(common),
            "coverage_percent": round(coverage_pct, 2),
            "missing_from_map": sorted(list(missing_from_map)),
            "extra_in_map": sorted(list(extra_in_map)),
        }
        
        with open("category_coverage_analysis.json", "w") as f:
            json.dump(comparison, f, indent=2)
        
        print(f"\n✅ Detailed analysis saved to: category_coverage_analysis.json")
    else:
        print("\n⚠️  LowesMap.txt not found")
        
        # Save sitemap categories
        with open("sitemap_all_categories.txt", "w") as f:
            for url in sorted(normalized):
                f.write(url + "\n")
        
        print(f"✅ Saved {len(normalized)} sitemap categories to: sitemap_all_categories.txt")
