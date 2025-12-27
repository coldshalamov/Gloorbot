import json
import os

def build_tree(data):
    # Sort categories by path length (parents first)
    sorted_ids = sorted(data.keys(), key=lambda x: len(data[x]['path']))
    
    tree = {} # id -> {children: [], is_redundant: False, count: 0}
    
    for cid in sorted_ids:
        cat = data[cid]
        path = cat['path'].lower().rstrip('/')
        
        # Look for a parent in the already-processed tree
        potential_parent = None
        for pid, pnode in tree.items():
            parent_path = data[pid]['path'].lower().rstrip('/')
            if path.startswith(parent_path + "/"):
                # Path A/B/C starts with A/B/
                # Check for "longest" prefix to find immediate parent
                if potential_parent is None or len(data[pid]['path']) > len(data[potential_parent]['path']):
                    potential_parent = pid
        
        tree[cid] = {
            "name": cat['name'],
            "path": cat['path'],
            "parent_id": potential_parent,
            "children": []
        }
        
        if potential_parent:
            tree[potential_parent]['children'].append(cid)
            
    return tree

def main():
    if not os.path.exists("site_tree_discovery.json"):
        print("Data not found yet.")
        return
        
    with open("site_tree_discovery.json", "r") as f:
        data = json.load(f)
        
    tree = build_tree(data)
    
    # Identify Leaf Nodes (those with no children)
    leafs = [cid for cid, node in tree.items() if not node['children']]
    roots = [cid for cid, node in tree.items() if not node['parent_id']]
    
    print(f"Tree Analysis:")
    print(f"  Total Nodes: {len(tree)}")
    print(f"  Root Nodes: {len(roots)}")
    print(f"  Leaf Nodes: {len(leafs)}")
    
    # Save tree for visualization or further processing
    with open("site_hierarchical_tree.json", "w") as f:
        json.dump(tree, f, indent=2)

if __name__ == "__main__":
    main()
