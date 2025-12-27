import json
import re
import os

def get_id(url):
    match = re.search(r'/(\d+)$', url.strip())
    return match.group(1) if match else None

def main():
    # 1. Load the current list
    input_file = "LowesMap_Optimized_Safe.txt"
    output_file = "LowesMap_Final_Pruned.txt"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Map ID -> URL
    id_to_url = {get_id(url): url for url in urls if get_id(url)}
    ids_in_list = set(id_to_url.keys())

    # 2. Load the tree
    tree_file = "site_hierarchical_tree.json"
    if not os.path.exists(tree_file):
        print(f"Error: {tree_file} not found.")
        return

    with open(tree_file, "r") as f:
        tree = json.load(f)

    # 3. Identify redundant parents
    # A parent is redundant if all its children (or a sufficient subset) are already in the list
    # OR if any child is in the list (since the child is more granular).
    redundant_ids = set()
    for cid in ids_in_list:
        node = tree.get(cid)
        if node and node.get('children'):
            # If any of this node's children are ALSO in the list, then this node is a "Parent redundant"
            # because we are scraping the more specific children.
            children_in_list = [child_id for child_id in node['children'] if child_id in ids_in_list]
            if children_in_list:
                redundant_ids.add(cid)
                print(f"Pruning redundant parent {cid} ({node.get('name')}) because children {children_in_list} are present.")

    # 4. Create the pruned list
    final_urls = [url for id, url in id_to_url.items() if id not in redundant_ids]

    with open(output_file, "w") as f:
        for url in sorted(final_urls):
            f.write(url + "\n")

    print(f"\nOriginal count: {len(ids_in_list)}")
    print(f"Pruned count: {len(final_urls)}")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
