
def check_overlap():
    input_file = "PARALLEL/urls_refined.txt"
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # 1. Check for Duplicate IDs (Strict Redundancy)
    id_map = {}
    duplicates = []
    
    for url in urls:
        parts = url.split('/')
        if not parts: continue
        last_segment = parts[-1]
        # Extract the numeric ID part
        import re
        ids = re.findall(r'\d+', last_segment)
        if ids:
            # Usually the first long number is the category ID
            cat_id = ids[0]
            if cat_id in id_map:
                duplicates.append((cat_id, id_map[cat_id], url))
            else:
                id_map[cat_id] = url
                
    print(f"\n1. Exact Duplicates (Same Category ID): {len(duplicates)}")
    if duplicates:
        print("   (These are literal duplicate pages with different URL names)")
        for d in duplicates[:5]:
            print(f"   ID {d[0]}:")
            print(f"     A: {d[1]}")
            print(f"     B: {d[2]}")

    # 2. Check for Parent/Child Overlap (Hierarchy Redundancy)
    # We look for textual path prefixes.
    # Ex: /pl/furniture/123 vs /pl/furniture/chairs/456
    
    # Sort by length so short (parents) come first? 
    # Actually just simple string comparisons.
    
    overlap_count = 0
    # Clean URLs to just the path part for comparison
    paths = []
    for url in urls:
        # strip https://www.lowes.com
        if 'lowes.com' in url:
            path = url.split('lowes.com')[1]
        else:
            path = url
        # remove the numeric ID at the end to compare string "topics"
        # e.g. /pl/furniture/chairs/ -> compare to /pl/furniture/
        base_path = re.sub(r'/\d+[-]?.*$', '', path)
        paths.append((base_path, url))
        
    paths.sort(key=lambda x: len(x[0])) # Sort by length
    
    likely_parents = []
    
    # This is O(N^2) roughly but N=3600 is small enough
    # We check if path A is a prefix of path B
    
    for i in range(len(paths)):
        parent_cand, parent_url = paths[i]
        # We only care about meaningful parents, e.g. /pl/furniture
        if len(parent_cand) < 5: continue 
        
        is_parent = False
        children = []
        
        for j in range(len(paths)):
            if i == j: continue
            child_cand, child_url = paths[j]
            
            # Check if parent is prefix of child (and child adds distinct subcategory)
            # e.g. /pl/furniture vs /pl/furniture/chairs
            if child_cand.startswith(parent_cand + '/'):
                is_parent = True
                children.append(child_url)
                if len(children) > 3: break # Found enough proof
        
        if is_parent:
            likely_parents.append((parent_url, children))

    print(f"\n2. Hierarchy Overlaps: {len(likely_parents)} parent categories detected.")
    print("   (Scraping these is redundant if we also scrape their children)")
    
    for p in likely_parents[:10]:
        print(f"   Parent: {p[0]}")
        print(f"     -> Has {len(p[1])}+ children like: {p[1][0]}")

    print(f"\nSummary:")
    print(f"Total URLs: {len(urls)}")
    print(f"Leaf Nodes (approx): {len(urls) - len(likely_parents)}")

if __name__ == "__main__":
    check_overlap()
