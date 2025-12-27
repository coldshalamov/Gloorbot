import json
import re
import os

def get_id(url):
    match = re.search(r'/(\d+)$', url.strip())
    return match.group(1) if match else None

def main():
    # Load 716 List
    with open("LowesMap_Final_Pruned.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    url_map = {get_id(u): u for u in urls}
    active_ids = set(url_map.keys())

    # Load Tree
    with open("site_hierarchical_tree.json", "r") as f:
        tree = json.load(f)

    # Find Collapsibles
    # Group active IDs by their PARENT
    parent_map = {} # parent_id -> [child_id, child_id]
    
    for cid in active_ids:
        node = tree.get(cid)
        if not node: continue
        
        pid = node.get('parent_id')
        if pid:
            if pid not in parent_map:
                parent_map[pid] = []
            parent_map[pid].append(cid)

    # Identify Candidates
    candidates = []
    print("Candidates for Collapsing (Bottom-Up Pruning):")
    print("----------------------------------------------")
    
    for pid, children in parent_map.items():
        # If a parent has multiple children in our list, it's a candidate for collapsing
        # IF the parent's total count is < 2000.
        if len(children) > 1:
            pnode = tree.get(pid)
            pname = pnode.get('name', 'Unknown') if pnode else 'Unknown'
            # Construct parent URL if possible
            purl = f"https://www.lowes.com/pl/{pname.replace(' ', '-')}/{pid}"
            
            candidates.append({
                "parent_id": pid,
                "parent_name": pname,
                "children_count": len(children),
                "children_ids": children,
                "example_url": purl
            })
            print(f"Parent: {pname} ({pid}) has {len(children)} active children.")

    # Save candidates for a check script
    with open("candidates_for_collapsing.json", "w") as f:
        json.dump(candidates, f, indent=2)
        
    print(f"\nFound {len(candidates)} parent categories that could potentially replace their children.")

if __name__ == "__main__":
    main()
