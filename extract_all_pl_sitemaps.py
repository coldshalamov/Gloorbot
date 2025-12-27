import requests
import xml.etree.ElementTree as ET
import re
import json

def fetch_sitemap_index():
    url = "https://www.lowes.com/sitemap.xml"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        root = ET.fromstring(r.text)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [loc.text for loc in root.findall('.//ns:loc', ns)]
    return []

def extract_pl_urls(sitemap_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(sitemap_url, headers=headers, timeout=10)
        if r.status_code != 200: return []
        
        # Look for /pl/ in the text without full XML parsing for speed
        urls = re.findall(r'https://www.lowes.com/pl/[^<"\s]+', r.text)
        return urls
    except:
        return []

def main():
    sitemaps = fetch_sitemap_index()
    print(f"Found {len(sitemaps)} sitemaps.")
    
    all_pl_urls = set()
    
    for i, sm in enumerate(sitemaps):
        print(f"[{i}/{len(sitemaps)}] Checking {sm}")
        urls = extract_pl_urls(sm)
        for u in urls:
            # Clean store params from sitemap URLs
            base_url = u.split('?')[0].rstrip('/')
            all_pl_urls.add(base_url)
            
        if i % 50 == 0 and i > 0:
            print(f"  Found {len(all_pl_urls)} unique /pl/ URLs so far...")
            
    print(f"Total unique /pl/ URLs found: {len(all_pl_urls)}")
    
    with open("master_sitemap_pl_list.txt", "w") as f:
        for u in sorted(all_pl_urls):
            f.write(u + "\n")

if __name__ == "__main__":
    main()
