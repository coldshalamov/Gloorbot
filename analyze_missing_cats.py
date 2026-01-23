import re
from pathlib import Path
from urllib.parse import urlparse

def get_root_category(url):
    # url form: https://www.lowes.com/pl/root-cat/sub-cat/id
    # or: https://www.lowes.com/pl/root-cat/id
    try:
        path = urlparse(url.strip()).path
        parts = path.split('/')
        if len(parts) > 2 and parts[1] == 'pl':
            return parts[2]
    except:
        pass
    return None

def analyze():
    existing_roots = set()
    
    # 1. Load existing
    with open('PARALLEL/urls.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if '/pl/' in line:
                root = get_root_category(line)
                if root:
                    existing_roots.add(root)
    
    print(f"Found {len(existing_roots)} existing root categories.")
    
    # 2. Scan sitemap
    sitemap_roots = {} # root -> example_url
    
    with open('master_sitemap_pl_list.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if '/pl/' not in line:
                continue
            
            root = get_root_category(line)
            if root and root not in existing_roots:
                if root not in sitemap_roots:
                    sitemap_roots[root] = line.strip()
                    
    print(f"Found {len(sitemap_roots)} potential missing root categories.")
    
    output_path = Path('discovered/sitemap_missing_candidates.txt')
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Missing Root Categories from master_sitemap_pl_list.txt\n")
        f.write(f"# Total Found: {len(sitemap_roots)}\n\n")
        
        for root in sorted(sitemap_roots.keys()):
            f.write(f"{root}\t{sitemap_roots[root]}\n")
            
    print(f"Saved results to {output_path}")
        
    # Check for specific user mentions
    print("\nSpecific checks:")
    for kw in ['pet', 'clean', 'personal']:
        matches = [r for r in sitemap_roots.keys() if kw in r.lower()]
        print(f"Roots containing '{kw}': {matches}")

if __name__ == '__main__':
    analyze()
