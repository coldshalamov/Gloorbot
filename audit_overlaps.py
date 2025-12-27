import json
import re

def main():
    with open("master_candidate_ids.json", "r") as f:
        master = json.load(f) # id -> url
        
    # Group by potential overlapping paths
    # We want to find nodes that have descendants in the list
    tree = {} # id -> [descendant_ids]
    
    sorted_ids = sorted(master.keys(), key=lambda x: master[x].count('/'))
    
    for i, cid in enumerate(sorted_ids):
        url = master[cid]
        path = url.split('/pl/')[1].split('/')[0] # Path string like 'washers-dryers/washing-machines'
        
        descendants = []
        for other_cid in sorted_ids[i+1:]:
            other_url = master[other_cid]
            other_path = other_url.split('/pl/')[1].split('/')[0]
            if other_path.startswith(path + "/"):
                descendants.append(other_cid)
        
        if descendants:
            tree[cid] = descendants

    print(f"Overlap Audit:")
    print(f"  Total Unique Categories: {len(master)}")
    print(f"  Categories with Descendants in List: {len(tree)}")
    
    # Calculate potential savings if all parents were < 2000
    potential_savings = sum(len(d) for d in tree.values())
    print(f"  Max Potential Redundant URLs: {potential_savings}")
    
    # Save for final audit
    with open("overlap_tree.json", "w") as f:
        json.dump(tree, f, indent=2)

if __name__ == "__main__":
    main()
