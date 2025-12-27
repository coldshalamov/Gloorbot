"""
Find category sitemap in Lowe's sitemap index
"""
import requests
import xml.etree.ElementTree as ET

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

def parse_sitemap_index(content):
    sitemaps = []
    try:
        root = ET.fromstring(content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for sitemap in root.findall('.//ns:sitemap', ns):
            loc = sitemap.find('ns:loc', ns)
            if loc is not None and loc.text:
                sitemaps.append(loc.text)
        return sitemaps
    except:
        return []

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

print("Fetching sitemap index...")
index_content = fetch_sitemap("https://www.lowes.com/sitemap.xml")

if index_content:
    sitemaps = parse_sitemap_index(index_content)
    print(f"Found {len(sitemaps)} sitemaps\n")
    
    # Look for category-specific sitemaps
    category_sitemaps = [s for s in sitemaps if 'category' in s.lower() or 'pl' in s.lower()]
    
    if category_sitemaps:
        print(f"Found {len(category_sitemaps)} potential category sitemaps:")
        for sm in category_sitemaps:
            print(f"  - {sm}")
    else:
        print("No obvious category sitemaps found.")
        print("\nAll sitemaps:")
        for sm in sitemaps:
            print(f"  - {sm}")
    
    # Check a few non-detail sitemaps
    print("\n" + "="*60)
    print("Checking non-detail sitemaps for categories...")
    print("="*60)
    
    non_detail = [s for s in sitemaps if 'detail' not in s.lower()]
    
    for sitemap_url in non_detail[:10]:  # Check first 10 non-detail sitemaps
        print(f"\nChecking: {sitemap_url}")
        content = fetch_sitemap(sitemap_url)
        if content:
            urls = parse_urls(content)
            pl_urls = [u for u in urls if '/pl/' in u]
            if pl_urls:
                print(f"  ✅ FOUND {len(pl_urls)} category URLs!")
                print(f"  Sample: {pl_urls[0]}")
                
                # Save all category URLs
                with open("sitemap_categories_found.txt", "w") as f:
                    for url in sorted(pl_urls):
                        f.write(url + "\n")
                
                print(f"\n✅ Saved {len(pl_urls)} category URLs to: sitemap_categories_found.txt")
                break
            else:
                print(f"  No category URLs (has {len(urls)} total URLs)")
else:
    print("Failed to fetch sitemap index")
