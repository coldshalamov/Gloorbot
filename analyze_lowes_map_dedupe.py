import re
from pathlib import Path
import json

def analyze_urls(file_path):
    map_path = Path(file_path)
    if not map_path.exists():
        print(f"Error: {file_path} not found")
        return

    with open(map_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    urls = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '/pl/' in line:
            urls.append(line)

    results = []
    for url in urls:
        # Extract ID (usually at the end)
        # Structure: .../pl/Text-Path/ID
        match = re.search(r'/pl/.*?/(\d+)', url)
        cat_id = match.group(1) if match else None
        
        # Extract path components
        path_match = re.search(r'/pl/(.*?)/\d+', url)
        path_str = path_match.group(1) if path_match else ""
        path_parts = path_str.split('-')
        
        results.append({
            "url": url,
            "id": cat_id,
            "path": path_str,
            "parts": path_parts
        })

    # Find duplicate IDs
    id_counts = {}
    for r in results:
        if r["id"]:
            id_counts[r["id"]] = id_counts.get(r["id"], []) + [r["path"]]

    duplicate_ids = {k: v for k, v in id_counts.items() if len(v) > 1}

    # Find hierarchical overlaps (strings like 'Batteries' vs 'Batteries-Electrical')
    # Or 'Tools' vs 'Power-Tools'
    
    # Sort by path length
    sorted_paths = sorted([r["path"] for r in results], key=len)
    
    hierarchy = []
    for i, short_path in enumerate(sorted_paths):
        children = []
        for longer_path in sorted_paths[i+1:]:
            if short_path in longer_path: # Naive check
                children.append(longer_path)
        if children:
            hierarchy.append({
                "parent": short_path,
                "potential_children": children[:5] # Limit to 5 for view
            })

    output = {
        "total_urls": len(results),
        "unique_ids": len(id_counts),
        "duplicate_ids_count": len(duplicate_ids),
        "duplicate_ids_sample": list(duplicate_ids.items())[:10],
        "potential_hierarchies": hierarchy[:10]
    }

    with open("url_dedupe_analysis.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Analyzed {len(results)} URLs.")
    print(f"Unique IDs: {len(id_counts)}")
    print(f"Duplicates: {len(duplicate_ids)}")
    print("Check url_dedupe_analysis.json for details.")

if __name__ == "__main__":
    analyze_urls("LowesMap.txt")
