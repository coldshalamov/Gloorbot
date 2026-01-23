
import re

def refine_urls_strict():
    input_file = "sitemap_minimal_structural_urls.txt"
    # output_file = "PARALLEL/urls_refined.txt" 
    # Use a new name to distinguish
    output_file = "PARALLEL/urls_leaf_only.txt"
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        # Initial cleanup: lowercase, strip, ignore tesla domain
        urls = [line.strip().lower() for line in f if line.strip() and "tesla.myloweslife.com" not in line.lower()]

    print(f"Initial count: {len(urls)}")
    
    # 1. Structural Filtering (Length + Complexity)
    candidates = []
    unique_ids = set()
    
    for url in urls:
        parts = url.split('/')
        last_segment = parts[-1] 
        numeric_groups = re.findall(r'\d+', last_segment)
        
        # Filter 1: Too faceted (heuristic: >2 numeric groups in last segment)
        if len(numeric_groups) > 2:
            continue
            
        # Filter 2: Duplicate IDs
        if numeric_groups:
            # We track IDs but we don't discard yet if we are doing hierarchy check
            # Actually, standard sitemap shouldn't have duplicate IDs for different paths usually
            # But let's keep them all for now to check hierarchy
            pass
            
        candidates.append(url)
        
    print(f"Structural candidates: {len(candidates)}")
    
    # 2. Hierarchy Pruning (Remove Parents)
    # Sort by string length to make prefix checking easy? 
    # No, we need O(N^2) or a Trie. N=3600 is small enough for N^2.
    
    # Helper to clean URL for comparison (remove protocol and trailing ID)
    def get_path_concept(u):
        if 'lowes.com' in u:
            path = u.split('lowes.com')[1]
        else:
            path = u
        # Remove the ID part at the end
        return re.sub(r'/\d+[-]?.*$', '', path)

    # Sort by length descending ensures we process children before parents?
    # No, let's just mark parents for deletion if they identify a child.
    
    to_remove = set()
    
    # Create tuples of (original_url, concept_path)
    url_data = []
    for u in candidates:
        concept = get_path_concept(u)
        url_data.append({'url': u, 'concept': concept})
        
    # Check every pair
    for i in range(len(url_data)):
        parent = url_data[i]
        if parent['concept'] in ['/pl/', '/pl']: continue # Skip root if exists
        
        # If this 'parent' has a concept that is a prefix of another 'child' concept
        # AND that child is strictly longer (more segments)
        # Then 'parent' is redundant.
        
        # Optimize: meaningful parents usually have short paths.
        
        for j in range(len(url_data)):
            if i == j: continue
            child = url_data[j]
            
            # Prefix check
            if child['concept'].startswith(parent['concept'] + '/'):
                # Found a child! Parent is redundant.
                to_remove.add(parent['url'])
                break # One child is enough to prove parenthood
    
    print(f"Identified {len(to_remove)} parent categories to prune.")
    
    final_urls = [u for u in candidates if u not in to_remove]
    
    print(f"Final Leaf Nodes: {len(final_urls)}")
    
    # Write result
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Lowe's Structural LEAF Category List\n")
        f.write(f"# Total: {len(final_urls)} unique leaf categories\n")
        f.write("# Redundant parents have been pruned to prevent overlap\n\n")
        for u in sorted(final_urls):
            f.write(u + "\n")
            
    print(f"Written strict list to {output_file}")

if __name__ == "__main__":
    refine_urls_strict()
