import json
import re
import os

def get_id(url):
    match = re.search(r'/(\d+)$', url.split('?')[0].rstrip('/'))
    return match.group(1) if match else None

def main():
    # 1. Load User's List
    user_urls = []
    if os.path.exists("LowesMap.txt"):
        with open("LowesMap.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    user_urls.append(line)
    
    # 2. Load Discovered List
    discovered_data = {}
    if os.path.exists("site_tree_discovery.json"):
        with open("site_tree_discovery.json", "r") as f:
            discovered_data = json.load(f)
            
    # 3. Merge by ID
    master = {} # id -> url
    
    def add_to_master(urls):
        for u in urls:
            if '/pl/' not in u: continue
            cid = get_id(u)
            if cid:
                master[cid] = u

    add_to_master(user_urls)
    add_to_master([d['url'] for d in discovered_data.values()])
            
    print(f"Master List Size (Deduplicated by ID): {len(master)}")
    
    # 4. Save to master list
    with open("master_candidate_list.txt", "w") as f:
        for u in sorted(master.values()):
            f.write(u + "\n")
            
    # 5. Build Hierarchy and suggest Pruning
    # Sort by path depth
    sorted_urls = sorted(master.values(), key=lambda x: x.count('/'))
    
    pruned = []
    for i, url in enumerate(sorted_urls):
        is_covered = False
        # Check if any ALREADY ADDED URL is a parent of this one
        # A URL is a parent if its path is a prefix of our path.
        # But wait, Lowe's doesn't always use nested paths.
        # So we must rely on SITETREE or ACTUAL COUNTS.
        pass

    with open("master_candidate_ids.json", "w") as f:
        json.dump(master, f, indent=2)

if __name__ == "__main__":
    main()
