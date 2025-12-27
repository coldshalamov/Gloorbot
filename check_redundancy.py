import json
import re

def get_id(url):
    match = re.search(r'/(\d+)$', url.split('?')[0].rstrip('/'))
    return match.group(1) if match else None

def main():
    # Load Optimized List
    opt_ids = set()
    with open("LowesMap_Optimized_Safe.txt", "r") as f:
        for line in f:
            cid = get_id(line)
            if cid: opt_ids.add(cid)
            
    # Load Tree to check parent-child relationships
    try:
        with open("site_hierarchical_tree.json", "r") as f:
            tree_data = json.load(f)
    except:
        return

    redundant_parents = 0
    for cid in opt_ids:
        # Check if any of MY children are ALSO in the list
        node = tree_data.get(cid)
        if node and node.get('children'):
            children = node['children']
            overlap = [c for c in children if c in opt_ids]
            if overlap:
                redundant_parents += 1
                # print(f"Redundancy: Parent {cid} and Children {overlap} are both in list.")

    print(f"Redundancy Check: {redundant_parents} Parents are co-listed with their Children.")

if __name__ == "__main__":
    main()
