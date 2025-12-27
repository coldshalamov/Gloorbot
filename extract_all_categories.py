import requests
import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path

def fetch_sitemap(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        return r.text if r.status_code == 200 else None
    except:
        return None

def extract_categories():
    print("Extracting all categories from sitemaps...")
    all_cats = {} # id -> {url, name, path}
    
    for i in range(4):
        url = f"https://www.lowes.com/sitemap/lpl-refinements{i}.xml"
        print(f"  Fetching {url}")
        content = fetch_sitemap(url)
        if not content: continue
        
        try:
            root = ET.fromstring(content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for loc in root.findall('.//ns:loc', ns):
                u = loc.text
                # Example: https://www.lowes.com/pl/Above-ground-pools-Pools-Outdoors/4294610203?storeId=2793&...
                match = re.search(r'/pl/(.*?)/(\d+)', u)
                if match:
                    path_str = match.group(1)
                    cat_id = match.group(2)
                    clean_url = f"https://www.lowes.com/pl/{path_str}/{cat_id}"
                    
                    if cat_id not in all_cats:
                        all_cats[cat_id] = {
                            "url": clean_url,
                            "path": path_str,
                            "id": cat_id
                        }
        except:
            continue
            
    return all_cats

def main():
    categories = extract_categories()
    print(f"Found {len(categories)} unique Category IDs in sitemaps.")
    
    with open("master_category_list.json", "w") as f:
        json.dump(categories, f, indent=2)
    
    # Also save as a simple text list
    with open("master_category_urls.txt", "w") as f:
        for cat in sorted(categories.values(), key=lambda x: x['path']):
            f.write(f"{cat['url']}\n")

if __name__ == "__main__":
    main()
