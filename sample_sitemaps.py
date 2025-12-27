"""
Quick sitemap sampler - check first few sitemaps to understand structure
"""
import requests
import xml.etree.ElementTree as ET

def fetch_sitemap(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
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

print("Sampling first 5 sitemaps to understand structure...")

for i in range(5):
    url = f"https://www.lowes.com/sitemap/detail{i}.xml"
    print(f"\n[{i+1}/5] {url}")
    content = fetch_sitemap(url)
    if content:
        urls = parse_urls(content)
        print(f"  Total URLs: {len(urls)}")
        
        # Categorize URLs
        pl_urls = [u for u in urls if '/pl/' in u]
        pd_urls = [u for u in urls if '/pd/' in u]
        store_urls = [u for u in urls if '/store/' in u]
        other_urls = [u for u in urls if '/pl/' not in u and '/pd/' not in u and '/store/' not in u]
        
        print(f"  Category pages (/pl/): {len(pl_urls)}")
        print(f"  Product detail (/pd/): {len(pd_urls)}")
        print(f"  Store pages (/store/): {len(store_urls)}")
        print(f"  Other: {len(other_urls)}")
        
        if pl_urls:
            print(f"  Sample category URL: {pl_urls[0]}")
        if pd_urls:
            print(f"  Sample product URL: {pd_urls[0]}")

print("\n" + "="*60)
print("CONCLUSION:")
print("If most sitemaps contain /pd/ (product detail) pages,")
print("we should focus on finding the category (/pl/) sitemap.")
print("="*60)
