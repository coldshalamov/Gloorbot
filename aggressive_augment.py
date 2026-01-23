
import re

def aggressive_augment():
    current_file = 'SHOP_ALL_URLS_GENERATED.txt'
    master_file = 'master_sitemap_pl_list.txt'
    output_file = 'SHOP_ALL_URLS_AUGMENTED_V2.txt'
    
    # 1. Load Current IDs
    current_ids = set()
    current_urls = []
    
    with open(current_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                current_urls.append(line.strip())
                # Extract ID
                # /pl/foo/bar/12345
                match = re.search(r'/(\d+)(?:\?|$)', line)
                if match:
                    current_ids.add(match.group(1))
                    
    print(f"Loaded {len(current_ids)} unique IDs from current list.")
    
    # 2. Scan Sitemap
    to_add = []
    seen_ids = set()
    
    with open(master_file, 'r', encoding='utf-8') as f:
        for line in f:
            raw = line.strip()
            # Extract URL
            match = re.search(r'<loc>(.*?)</loc>', raw)
            if match:
                url = match.group(1)
            elif raw.startswith('https'):
                url = raw
            else:
                continue
                
            if '/pl/' not in url: continue
            if 'lowesbrands' in url or 'departments' in url: continue
            
            # Extract ID
            id_match = re.search(r'/(\d+)$', url)
            if not id_match: continue # No numeric ID at end? Skip
            
            sitemap_id = id_match.group(1)
            
            # If we already have this ID, skip
            if sitemap_id in current_ids: continue
            if sitemap_id in seen_ids: continue
            
            # It's a NEW ID.
            # But is it relevant?
            # User wants "Shop All" pages.
            # Usually these have IDs. 
            # We want to catch things like "pet-food" (ID: 2710431208428)
            
            # Filter logic:
            # If the URL depth is reasonably high (meaning it's a leaf or specific category)
            # OR if it seems to be a missing "Parent" (shorter URL)
            
            # Let's add it if it contains key terms we know we missed, OR generic safety
            # Actually, let's just add ALL PL URLs that have IDs we don't possess.
            # The risk is adding "Product" pages vs "PL" pages?
            # /pl/ means Product List. So these ARE categories.
            # (Product Detail Pages are /pd/)
            
            # So ANY /pl/ url in the sitemap that we don't have is a missing category.
            to_add.append(url)
            seen_ids.add(sitemap_id)
            
    print(f"Found {len(to_add)} missing /pl/ categories from Sitemap.")
    
    # Write
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Shop All URLs V2 - Aggressively Augmented\n")
        f.write(f"# Original: {len(current_urls)}\n")
        f.write(f"# Added: {len(to_add)}\n\n")
        
        for u in current_urls:
            f.write(u + "\n")
            
        f.write("\n# --- FROM SITEMAP ---\n")
        for u in to_add:
            f.write(u + "?goToProdList=true\n")
            
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    aggressive_augment()
