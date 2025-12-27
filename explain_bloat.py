import json
import re

def get_id(url):
    match = re.search(r'/(\d+)$', url.split('?')[0].rstrip('/'))
    return match.group(1) if match else None

def main():
    user_ids = set()
    with open("LowesMap.txt", "r") as f:
        for line in f:
            cid = get_id(line)
            if cid: user_ids.add(cid)
            
    opt_ids = set()
    with open("LowesMap_Optimized_Safe.txt", "r") as f:
        for line in f:
            cid = get_id(line)
            if cid: opt_ids.add(cid)
            
    # Load Tree
    try:
        with open("site_hierarchical_tree.json", "r") as f:
            tree_data = json.load(f) # id -> node
    except:
        print("Tree file missing")
        return

    # Check for "Unpacking"
    # Find user IDs that are PARENTS in the tree
    # And check if their CHILDREN are in the Optimized List
    
    unpacked_event = 0
    new_coverage_event = 0
    
    new_ids = opt_ids - user_ids
    
    for nid in new_ids:
        # Check if this ID descends from a User ID
        parent = tree_data.get(nid, {}).get('parent_id')
        is_unpacking = False
        
        # Traverse up
        curr = nid
        while curr:
            curr = tree_data.get(curr, {}).get('parent_id')
            if curr in user_ids:
                is_unpacking = True
                break
                
        if is_unpacking:
            unpacked_event += 1
        else:
            new_coverage_event += 1
            
    print(f"Explanation of {len(new_ids)} added URLs:")
    print(f"  Necessary Unpacking (Child of User URL): {unpacked_event}")
    print(f"  New Coverage (Missing Department): {new_coverage_event}")

if __name__ == "__main__":
    main()
