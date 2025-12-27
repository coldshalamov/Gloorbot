"""
Sitemap Analysis Script - Parse Lowe's sitemap for category URLs
"""
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import json

def fetch_sitemap():
    """Fetch Lowe's sitemap."""
    print("Fetching sitemap from Lowe's...")
    
    # Try common sitemap locations
    sitemap_urls = [
        "https://www.lowes.com/sitemap.xml",
        "https://www.lowes.com/sitemap_index.xml",
        "https://www.lowes.com/robots.txt",  # Check robots.txt for sitemap location
    ]
    
    for url in sitemap_urls:
        try:
            print(f"Trying: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Found: {url}")
                return response.text, url
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    return None, None

def parse_sitemap(content, source_url):
    """Parse sitemap XML and extract category URLs."""
    category_urls = set()
    
    try:
        # Handle sitemap index (links to other sitemaps)
        if 'sitemap_index' in source_url or '<sitemapindex' in content:
            print("Detected sitemap index, parsing sub-sitemaps...")
            root = ET.fromstring(content)
            
            # Extract sitemap URLs
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            sitemap_locs = root.findall('.//ns:loc', ns)
            
            for loc in sitemap_locs:
                sitemap_url = loc.text
                print(f"Fetching sub-sitemap: {sitemap_url}")
                try:
                    sub_response = requests.get(sitemap_url, timeout=10)
                    if sub_response.status_code == 200:
                        sub_urls = parse_sitemap(sub_response.text, sitemap_url)
                        category_urls.update(sub_urls)
                except Exception as e:
                    print(f"Error fetching {sitemap_url}: {e}")
        
        # Parse regular sitemap
        else:
            root = ET.fromstring(content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Find all <loc> tags
            locs = root.findall('.//ns:loc', ns)
            
            for loc in locs:
                url = loc.text
                if url and '/pl/' in url:
                    # Normalize
                    base_url = url.split('?')[0].rstrip('/')
                    category_urls.add(base_url)
    
    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        # Try robots.txt parsing
        if 'robots.txt' in source_url:
            for line in content.split('\n'):
                if line.strip().lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    print(f"Found sitemap in robots.txt: {sitemap_url}")
                    try:
                        response = requests.get(sitemap_url, timeout=10)
                        if response.status_code == 200:
                            return parse_sitemap(response.text, sitemap_url)
                    except Exception as e:
                        print(f"Error: {e}")
    
    return category_urls

def load_lowesmap():
    """Load URLs from LowesMap.txt."""
    map_path = Path("LowesMap.txt")
    if not map_path.exists():
        return []
    
    urls = []
    with open(map_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '/pl/' in line:
                base_url = line.split('?')[0].rstrip('/')
                urls.append(base_url)
    
    return sorted(list(set(urls)))

def main():
    print("="*60)
    print("SITEMAP ANALYSIS")
    print("="*60)
    
    # Fetch sitemap
    content, source_url = fetch_sitemap()
    
    if not content:
        print("\n❌ Could not fetch sitemap. Lowe's may not have a public sitemap or it's blocked.")
        return
    
    # Parse sitemap
    print("\nParsing sitemap for category URLs...")
    sitemap_urls = parse_sitemap(content, source_url)
    print(f"Found {len(sitemap_urls)} category URLs in sitemap")
    
    # Load LowesMap.txt
    print("\nLoading LowesMap.txt...")
    map_urls = load_lowesmap()
    print(f"Found {len(map_urls)} URLs in LowesMap.txt")
    
    # Compare
    sitemap_set = set(sitemap_urls)
    map_set = set(map_urls)
    
    missing = sitemap_set - map_set
    extra = map_set - sitemap_set
    common = sitemap_set & map_set
    
    report = {
        "sitemap_urls": len(sitemap_urls),
        "lowesmap_urls": len(map_urls),
        "common": len(common),
        "missing_from_map": len(missing),
        "extra_in_map": len(extra),
        "missing_urls": sorted(list(missing))[:50],  # First 50
    }
    
    # Save
    with open("sitemap_analysis.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Print
    print("\n" + "="*60)
    print("SITEMAP COMPARISON")
    print("="*60)
    print(f"Sitemap URLs:          {report['sitemap_urls']}")
    print(f"LowesMap.txt URLs:     {report['lowesmap_urls']}")
    print(f"Common URLs:           {report['common']}")
    print(f"Missing from Map:      {report['missing_from_map']}")
    print(f"Extra in Map:          {report['extra_in_map']}")
    
    if missing:
        print(f"\n⚠️  {len(missing)} URLs in sitemap but not in LowesMap.txt (first 10):")
        for url in sorted(list(missing))[:10]:
            print(f"  - {url}")
    
    print(f"\n✅ Report saved to: sitemap_analysis.json")

if __name__ == "__main__":
    main()
