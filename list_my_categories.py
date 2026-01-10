
import re
from pathlib import Path

def extract_category_names():
    urls_file = Path("PARALLEL/urls.txt")
    if not urls_file.exists():
        print(f"Error: {urls_file} not found")
        return

    categories = []
    with open(urls_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Only process lines with /pl/ that aren't commented out
            if line and not line.startswith('#') and '/pl/' in line:
                # Extract the part between /pl/ and the last segment (the ID)
                # Examples:
                # /pl/air-conditioners-fans/blower-fans/2667787286 -> air-conditioners-fans/blower-fans
                # /pl/Appliances/4294857975 -> Appliances
                
                parts = line.split('/pl/')
                if len(parts) > 1:
                    path_content = parts[1].split('?')[0].rstrip('/')
                    path_segments = path_content.split('/')
                    
                    if len(path_segments) >= 2:
                        # Hierarchical path, joined back together but without the trailing ID
                        category_name = " > ".join(path_segments[:-1])
                    else:
                        # Single segment or unusual format
                        category_name = path_segments[0]
                    
                    categories.append(category_name)

    # Sort and remove duplicates (though user said they pruned it already)
    # We'll just keep the order from the file but clean it up.
    
    print("### Categories in PARALLEL scraper ###\n")
    unique_depts = set()
    for cat in categories:
        dept = cat.split(' > ')[0].replace('-', ' ').title()
        unique_depts.add(dept)
        print(f"- {cat}")
    
    print(f"\nTotal Categories: {len(categories)}")
    print(f"Primary Departments involved: {', '.join(sorted(list(unique_depts)))}")

if __name__ == "__main__":
    extract_category_names()
