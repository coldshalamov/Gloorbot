
import re

def final_merge():
    current_file = 'SHOP_ALL_URLS_GENERATED.txt'
    master_file = 'master_sitemap_pl_list.txt'
    output_file = 'SHOP_ALL_URLS_FINAL.txt'
    
    # 1. Load Current Content
    existing_urls = []
    existing_ids = set()
    
    with open(current_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                url = line.strip().split('?')[0] # Remove query for ID check
                existing_urls.append(line.strip())
                
                # Extract ID
                match = re.search(r'/(\d+)$', url)
                if not match:
                    # Try finding ID inside path if faceted
                    # .../12345/product...
                    match = re.search(r'/(\d+)/', url)
                    
                if match:
                    existing_ids.add(match.group(1))
                    
    print(f"Loaded {len(existing_urls)} existing URLs ({len(existing_ids)} unique IDs).")
    
    # 2. Scan Master Sitemap
    to_add = []
    
    with open(master_file, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if not url.startswith('http'): continue
            
            # Extract ID
            match = re.search(r'/(\d+)$', url)
            if match:
                sitemap_id = match.group(1)
                
                if sitemap_id not in existing_ids:
                    # New ID! 
                    to_add.append(url)
                    existing_ids.add(sitemap_id) # Prevent duplicates in addition
                    
    print(f"Found {len(to_add)} NEW IDs from Sitemap.")
    
    # 3. Write Final
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Shop All URLs - Final Combined\n")
        f.write(f"# Original: {len(existing_urls)}\n")
        f.write(f"# Sitemap Additions: {len(to_add)}\n\n")
        
        for u in existing_urls:
            f.write(u + "\n")
            
        f.write("\n# --- SITEMAP ADDITIONS ---\n")
        for u in sorted(to_add):
            f.write(u + "?goToProdList=true\n")
            
    print(f"Success! Final list written to {output_file}")

if __name__ == "__main__":
    final_merge()
