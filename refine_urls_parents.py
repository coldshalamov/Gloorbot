
import re

def refine_urls_parents_priority():
    input_file = "sitemap_minimal_structural_urls.txt"
    output_file = "PARALLEL/urls_parents_only.txt"
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        # Initial cleanup: lowercase, strip, ignore tesla, sort
        urls = [line.strip().lower() for line in f if line.strip() and "tesla.myloweslife.com" not in line.lower()]

    print(f"Initial count: {len(urls)}")
    
    # 1. Structural Clean (remove obvious facets)
    clean_urls = []
    for url in urls:
        parts = url.split('/')
        last_segment = parts[-1] 
        numeric_groups = re.findall(r'\d+', last_segment)
        if len(numeric_groups) > 2:
            continue
        clean_urls.append(url)
        
    # 2. Logic: Keep PARENTS, discard CHILDREN
    # Sort by length ASCENDING.
    # If a URL starts with a URL we have already seen (minus ID), it is a child.
    
    # Needs purely concept path for comparison
    def get_concept(u):
        if 'lowes.com' in u:
            path = u.split('lowes.com')[1]
        else:
            path = u
        # Remove trailing ID
        return re.sub(r'/\d+[-]?.*$', '', path)

    # Sort candidates by length of concept (shortest first)
    # This ensures 'accessible-cooking' comes before 'accessible-cooking/accessible-cooktops'
    url_data = []
    for u in clean_urls:
        c = get_concept(u)
        url_data.append({'url': u, 'concept': c, 'len': len(c)})
        
    url_data.sort(key=lambda x: x['len'])
    
    final_urls = []
    accepted_concepts = set()
    
    skipped_count = 0
    
    for item in url_data:
        concept = item['concept']
        
        # Check if any existing accepted concept is a prefix of this concept
        # Since we sort by length, we only need to check if a SHORTER one matches
        
        is_child = False
        
        # This check is O(N*M) where M is accepted count. 
        # With 3000 items, 3000*3000 = 9M ops, trivial for python.
        
        for parent in accepted_concepts:
            # Check for directory prefix style match
            # parent: /pl/foo
            # child:  /pl/foo/bar
            # Must ensure slash to avoid /pl/foot matching /pl/foo
            
            p_check = parent
            if not p_check.endswith('/'):
                p_check += '/'
                
            if concept.startswith(p_check) or concept == parent:
                is_child = True
                break
        
        if is_child:
            skipped_count += 1
            # print(f"Skipping child: {concept} (Parent exists)")
        else:
            final_urls.append(item['url'])
            accepted_concepts.add(concept)
            
    print(f"Kept {len(final_urls)} parent categories.")
    print(f"Pruned {skipped_count} redundant child categories.")
    
    # Sort for file
    final_urls.sort()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Lowe's Structural PARENT Category List\n")
        f.write(f"# Total: {len(final_urls)} unique high-level categories\n")
        f.write("# Children pruned in favor of broadest parent categories\n\n")
        for u in final_urls:
            f.write(u + "\n")
            
    print(f"Written parent-priority list to {output_file}")

if __name__ == "__main__":
    refine_urls_parents_priority()
