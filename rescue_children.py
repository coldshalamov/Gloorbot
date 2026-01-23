
import re

def rescue_children():
    minimal_file = "sitemap_minimal_structural_urls.txt"
    master_file = "master_sitemap_pl_list.txt"
    output_file = "PARALLEL/urls_complete_leaves.txt"
    
    # 1. Load Structural (Minimal) List
    print(f"Reading {minimal_file}...")
    with open(minimal_file, 'r', encoding='utf-8') as f:
        minimal_urls = set(line.strip().lower() for line in f if line.strip() and "tesla" not in line)
        
    # 2. Identify Parents in Minimal List
    # A parent is any URL that matches the prefix of another URL in the set
    
    # Helper to clean ID
    def get_concept(u):
        if 'lowes.com' in u:
            path = u.split('lowes.com')[1]
        else:
            path = u
        return re.sub(r'/\d+[-]?.*$', '', path)

    clean_minimal = sorted(list(minimal_urls), key=len)
    parents_identified = set()
    
    # Simple O(N^2) prefix check
    for i in range(len(clean_minimal)):
        parent_url = clean_minimal[i]
        parent_c = get_concept(parent_url)
        if not parent_c.endswith('/'): parent_c += '/'
        
        for j in range(len(clean_minimal)):
            if i == j: continue
            child_url = clean_minimal[j]
            child_c = get_concept(child_url)
            
            if child_c.startswith(parent_c):
                parents_identified.add(parent_url)
                break
                
    print(f"Identified {len(parents_identified)} expandable parents in minimal list.")
    
    # 3. Rescue Missing Children from Master List
    # If we are pruning a parent, we must ensure ALL its structural children are in our list
    
    print(f"Scanning {master_file} for missing children...")
    
    rescued_children = set()
    
    # Pre-compute parent prefixes for fast lookup
    parent_prefixes = {} # prefix -> original_parent_url
    for p in parents_identified:
        c = get_concept(p)
        if not c.endswith('/'): c += '/'
        parent_prefixes[c] = p
        
    with open(master_file, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip().lower()
            if "tesla" in url: continue
            
            # Optimization: Quick filter
            if '/pl/' not in url: continue
            
            # Structural Check: Is it a valid category?
            # Must end in ID or ID-ID
            parts = url.split('/')
            last = parts[-1]
            # Heuristic: Faceted URLs often have more than 2 number groups "123-456-789"
            nums = re.findall(r'\d+', last)
            if len(nums) > 2: continue 
            
            # Concept extraction
            concept = get_concept(url)
            
            # Check if this URL is a child of any identified parent
            for p_concept, p_url in parent_prefixes.items():
                if concept.startswith(p_concept) and concept != p_concept:
                    # It is a child!
                    # Ensure it is an IMMEDIATE child (or structurally significant)
                    # Actually, if it's structural (passed num check), we want it.
                    
                    # Don't add if it's already in minimal
                    if url not in minimal_urls:
                        rescued_children.add(url)
                    break
                    
    print(f"Rescued {len(rescued_children)} missing children from Master List.")
    
    # 4. Merge and Final Leaf Prune
    combined_urls = minimal_urls.union(rescued_children)
    print(f"Combined Pool: {len(combined_urls)}")
    
    # Final Leaf Pruning on the expanded set
    # Same logic: if X is parent of Y, remove X.
    
    final_list = sorted(list(combined_urls), key=len)
    to_remove = set()
    
    # Optimization: Just use concepts again
    url_concepts = [(u, get_concept(u)) for u in final_list]
    
    for i in range(len(url_concepts)):
        p_url, p_c = url_concepts[i]
        if not p_c.endswith('/'): p_c += '/'
        
        for j in range(len(url_concepts)):
            if i == j: continue
            c_url, c_c = url_concepts[j]
            
            if c_c.startswith(p_c):
                to_remove.add(p_url)
                break
                
    final_leaves = [u for u in final_list if u not in to_remove]
    
    print(f"Final Complete Leaf Count: {len(final_leaves)}")
    
    # Validation: Check Lawn Mowers
    mower_count = 0
    for u in final_leaves:
        if 'lawn-mower' in u:
            mower_count += 1
            
    print(f"Lawn Mower Categories in Final List: {mower_count}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Lowe's Complete Structural Leaves\n\n")
        for u in sorted(final_leaves):
            f.write(u + "\n")
            
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    rescue_children()
