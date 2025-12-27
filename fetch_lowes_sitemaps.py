"""
Fetch and analyze Lowe's sitemaps to verify product category coverage
"""
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from urllib.parse import urlparse

def fetch_sitemap(url):
    """Fetch sitemap with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch {url}: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_sitemap_index(content):
    """Parse sitemap index to find all sub-sitemaps."""
    sitemaps = []
    try:
        root = ET.fromstring(content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Check if it's a sitemap index
        for sitemap in root.findall('.//ns:sitemap', ns):
            loc = sitemap.find('ns:loc', ns)
            if loc is not None and loc.text:
                sitemaps.append(loc.text)
        
        return sitemaps
    except Exception as e:
        print(f"Error parsing sitemap index: {e}")
        return []

def parse_sitemap_urls(content):
    """Parse sitemap to extract URLs."""
    urls = []
    try:
        root = ET.fromstring(content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url_elem in root.findall('.//ns:url', ns):
            loc = url_elem.find('ns:loc', ns)
            if loc is not None and loc.text:
                urls.append(loc.text)
        
        return urls
    except Exception as e:
        print(f"Error parsing sitemap URLs: {e}")
        return []

def main():
    print("="*60)
    print("LOWE'S SITEMAP ANALYSIS")
    print("="*60)
    
    # Try common sitemap locations
    sitemap_urls = [
        "https://www.lowes.com/sitemap.xml",
        "https://www.lowes.com/sitemap_index.xml",
        "https://www.lowes.com/sitemaps/sitemap.xml",
    ]
    
    # First, try to get robots.txt
    print("\n[1/4] Checking robots.txt...")
    robots_content = fetch_sitemap("https://www.lowes.com/robots.txt")
    
    if robots_content:
        print("✅ robots.txt fetched successfully")
        # Look for Sitemap: directives
        for line in robots_content.split('\n'):
            if line.strip().lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                if sitemap_url not in sitemap_urls:
                    sitemap_urls.insert(0, sitemap_url)
                print(f"   Found sitemap: {sitemap_url}")
    else:
        print("❌ Could not fetch robots.txt")
    
    # Try to fetch sitemap index
    print("\n[2/4] Fetching sitemap index...")
    sitemap_index_content = None
    sitemap_index_url = None
    
    for url in sitemap_urls:
        print(f"   Trying: {url}")
        content = fetch_sitemap(url)
        if content:
            sitemap_index_content = content
            sitemap_index_url = url
            print(f"   ✅ Found sitemap at: {url}")
            break
    
    if not sitemap_index_content:
        print("❌ Could not find any sitemap")
        return
    
    # Parse sitemap index
    print("\n[3/4] Parsing sitemap index...")
    sub_sitemaps = parse_sitemap_index(sitemap_index_content)
    
    if sub_sitemaps:
        print(f"✅ Found {len(sub_sitemaps)} sub-sitemaps")
        for i, sm in enumerate(sub_sitemaps[:10], 1):
            print(f"   {i}. {sm}")
        if len(sub_sitemaps) > 10:
            print(f"   ... and {len(sub_sitemaps) - 10} more")
    else:
        # Might be a regular sitemap, not an index
        print("   No sub-sitemaps found, parsing as regular sitemap...")
        sub_sitemaps = [sitemap_index_url]
    
    # Fetch and parse all sub-sitemaps
    print("\n[4/4] Extracting product category URLs...")
    all_category_urls = set()
    
    for i, sitemap_url in enumerate(sub_sitemaps, 1):
        print(f"   Processing sitemap {i}/{len(sub_sitemaps)}: {sitemap_url.split('/')[-1]}")
        content = fetch_sitemap(sitemap_url)
        if content:
            urls = parse_sitemap_urls(content)
            # Filter for /pl/ URLs (product listing pages)
            category_urls = [url for url in urls if '/pl/' in url]
            all_category_urls.update(category_urls)
            if category_urls:
                print(f"      Found {len(category_urls)} category URLs")
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Total category URLs in sitemap: {len(all_category_urls)}")
    
    # Load LowesMap.txt for comparison
    map_path = Path("LowesMap.txt")
    if map_path.exists():
        lowes_map_urls = set()
        with open(map_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '/pl/' in line:
                    # Normalize URL
                    base_url = line.split('?')[0].rstrip('/')
                    lowes_map_urls.add(base_url)
        
        print(f"URLs in LowesMap.txt: {len(lowes_map_urls)}")
        
        # Normalize sitemap URLs for comparison
        normalized_sitemap = {url.split('?')[0].rstrip('/') for url in all_category_urls}
        
        # Compare
        missing_from_map = normalized_sitemap - lowes_map_urls
        extra_in_map = lowes_map_urls - normalized_sitemap
        common = lowes_map_urls & normalized_sitemap
        
        print(f"Common URLs: {len(common)}")
        print(f"Missing from LowesMap.txt: {len(missing_from_map)}")
        print(f"Extra in LowesMap.txt (not in sitemap): {len(extra_in_map)}")
        
        if missing_from_map:
            print(f"\n⚠️  URLs in sitemap but NOT in LowesMap.txt (first 20):")
            for url in sorted(list(missing_from_map))[:20]:
                print(f"  - {url}")
        
        if extra_in_map:
            print(f"\n💡 URLs in LowesMap.txt but NOT in sitemap (first 20):")
            for url in sorted(list(extra_in_map))[:20]:
                print(f"  - {url}")
        
        # Save detailed comparison
        comparison = {
            "sitemap_total": len(all_category_urls),
            "lowesmap_total": len(lowes_map_urls),
            "common": len(common),
            "missing_from_map": sorted(list(missing_from_map)),
            "extra_in_map": sorted(list(extra_in_map)),
        }
        
        with open("sitemap_comparison.json", "w") as f:
            json.dump(comparison, f, indent=2)
        
        print(f"\n✅ Detailed comparison saved to: sitemap_comparison.json")
    else:
        print("\n⚠️  LowesMap.txt not found, cannot compare")
        
        # Save sitemap URLs
        with open("sitemap_categories.txt", "w") as f:
            for url in sorted(all_category_urls):
                f.write(url + "\n")
        
        print(f"✅ Sitemap URLs saved to: sitemap_categories.txt")
    
    print("="*60)

if __name__ == "__main__":
    main()
