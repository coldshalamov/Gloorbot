import json
import re

def build_tree(data):
    # Sort by path length
    sorted_ids = sorted(data.keys(), key=lambda x: data[x].count('/'))
    
    tree = {} # id -> {url, children: []}
    
    for cid in sorted_ids:
        url = data[cid]
        path_part = url.split('/pl/')[1].split('?')[0].rstrip('/') if '/pl/' in url else ""
        
        # Find immediate parent
        best_parent = None
        for pid, pnode in tree.items():
            ppath = pnode['path']
            if path_part.startswith(ppath + "/"):
                if best_parent is None or len(ppath) > len(tree[best_parent]['path']):
                    best_parent = pid
        
        tree[cid] = {
            "url": url,
            "path": path_part,
            "parent_id": best_parent,
            "children": []
        }
        if best_parent:
            tree[best_parent]['children'].append(cid)
            
    return tree

def main():
    if not os.path.exists("master_candidate_ids.json"): return
    with open("master_candidate_ids.json", "r") as f:
        master = json.load(f)
        
    tree = build_tree(master)
    
    roots = [cid for cid, node in tree.items() if not node['parent_id']]
    
    print(f"Hierarchy Summary:")
    print(f"  Unique Categories: {len(tree)}")
    print(f"  Root Categories: {len(roots)}")
    print(f"  Sub-categories: {len(tree) - len(roots)}")
    
    # Save tree for the lightweight auditor
    with open("hierarchical_basis_tree.json", "w") as f:
        json.dump(tree, f, indent=2)

if __name__ == "__main__":
    import os
    main()
