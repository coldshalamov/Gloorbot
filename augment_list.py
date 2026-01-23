
import re

def augment_shop_all_list():
    current_file = 'SHOP_ALL_URLS_GENERATED.txt'
    master_file = 'master_sitemap_pl_list.txt'
    output_file = 'SHOP_ALL_URLS_AUGMENTED.txt'
    
    print(f"Loading Base List: {current_file}...")
    
    current_urls = {}
    with open(current_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                # Normalize key: clean URL without query
                url = line.strip().split('?')[0].lower()
                current_urls[url] = line.strip()
                
    print(f"Base List Size: {len(current_urls)} URLs")
    
    # Analyze Coverage
    # Pre-compute "Concept Paths" for existing URLs to do hierarchy checking
    # e.g. /pl/pet-kennels-crates/ -> covered
    
    def get_concept(u):
        if 'lowes.com' in u:
            path = u.split('lowes.com')[1]
        else:
            path = u
        # Remove trailing last ID segment
        # e.g. /pl/foo/bar/123 -> /pl/foo/bar/
        return re.sub(r'/\d+[-]?.*$', '/', path)

    covered_concepts = set()
    for u in current_urls.keys():
        c = get_concept(u)
        covered_concepts.add(c)
        
    print(f"Unique concepts covered: {len(covered_concepts)}")
    
    print(f"Scanning Master Sitemap: {master_file}...")
    
    to_add = []
    
    with open(master_file, 'r', encoding='utf-8') as f:
        for line in f:
            raw_url = line.strip().lower()
            if not raw_url: continue
            if "lowesbrands" in raw_url or "departments" in raw_url or raw_url == "https://www.lowes.com": continue
            if "tesla" in raw_url: continue
            
            # Extract pure URL from XML if needed, or raw line
            if '<loc>' in raw_url:
                match = re.search(r'<loc>(.*?)</loc>', raw_url)
                if match:
                    url = match.group(1)
                else:
                    continue
            else:
                url = raw_url
                
            # Filter for PL (Product List) pages only
            if '/pl/' not in url: continue
            
            # Check overlap
            # 1. Is exact URL already there?
            if url in current_urls: continue
            
            # 2. Is this URL covered by a Parent concept in our list?
            # e.g. if we have /pl/pets/, we might say /pl/pets/food/ is covered
            # BUT user said his 'parent' lists are sometimes incomplete or messy.
            # However, if we add every child, we get 300k URLs.
            # We need a middle ground.
            
            # Strategy:
            # If the EXACT parent path (minus ID) exists in our list, we assume coverage?
            # NO, the user's list often has the "Child" ID but matches the "Parent" path concept.
            
            concept = get_concept(url)
            
            # If 'concept' is NOT in covered_concepts, it means we have NO representation for this aisle.
            # e.g. /pl/wheelchairs-mobility-aids/ is a concept. 
            # If user has NO URL that reduces to this path, he is missing the aisle.
            
            # However, what if user has /pl/wheelchairs-mobility-aids/walkers/ ?
            # That concept is /pl/wheelchairs-mobility-aids/walkers/
            # It does NOT cover /pl/wheelchairs-mobility-aids/ (the parent).
            
            # We want to fill gaps.
            # If we don't have this concept, AND we don't have a parent of this concept?
            
            # Let's simple check:
            # Do we have any URL that seems to cover this 'concept' or a parent of it?
            
            is_covered = False
            for covered in covered_concepts:
                if concept.startswith(covered): 
                    is_covered = True # A parent concept exists in our list
                    break
            
            if not is_covered:
                # Potential Candidate!
                # But wait, maybe this IS a parent of something we DO have?
                # e.g. New URL: /pl/pets/
                # We have: /pl/pets/food/
                # Should we add /pl/pets/? 
                # User prefers Leaf nodes usually, but if we missed the leaf...
                
                # Let's add it if it's a minimal leaf node itself (contains IDs)
                # Faceted URLs usually have >2 numeric groups. Simple cats have 1 or 2.
                
                parts = url.split('/')
                last = parts[-1]
                nums = re.findall(r'\d+', last)
                
                if len(nums) <= 2: 
                    to_add.append(url)

    print(f"Found {len(to_add)} new candidate URLs from sitemap gaps.")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Shop All URLs - Augmented (Base + Sitemap Gaps)\n")
        f.write(f"# Base: {len(current_urls)}\n")
        f.write(f"# Added: {len(to_add)}\n\n")
        
        # Write Original
        for line in current_urls.values():
            f.write(line + "\n")
            
        f.write("\n# --- AUGMENTED FROM SITEMAP ---\n")
        for u in sorted(to_add):
            f.write(u + "?goToProdList=true\n")
            
    print(f"Written augmented list to {output_file}")

if __name__ == "__main__":
    augment_shop_all_list()
