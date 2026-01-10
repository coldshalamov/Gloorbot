
import re
from pathlib import Path

def map_urls_to_categories():
    urls_file = Path("PARALLEL/urls.txt")
    if not urls_file.exists():
        print(f"Error: {urls_file} not found")
        return

    mapping = []
    with open(urls_file, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            # The scraper uses these exact lines (if they contain /pl/ and not back-aisle)
            if url and not url.startswith('#') and '/pl/' in url and 'the-back-aisle' not in url.lower():
                
                # Extract category name logic
                parts = url.split('/pl/')
                if len(parts) > 1:
                    path_content = parts[1].split('?')[0].rstrip('/')
                    path_segments = path_content.split('/')
                    
                    # Lowe's URLs usually end in a numeric ID, we ignore the last segment
                    if len(path_segments) >= 2:
                        name_segments = [s.replace('-', ' ').title() for s in path_segments[:-1]]
                        category_name = " > ".join(name_segments)
                    else:
                        category_name = path_segments[0].replace('-', ' ').title()
                    
                    mapping.append((category_name, url))

    # Output the mapping
    print(f"{'CATEGORY NAME':<60} | {'ACTUAL URL'}")
    print("-" * 140)
    
    with open("parallel_category_mapping.txt", "w", encoding="utf-8") as out:
        out.write(f"{'CATEGORY NAME':<60} | {'ACTUAL URL'}\n")
        out.write("-" * 140 + "\n")
        for name, url in mapping:
            line = f"{name:<60} | {url}"
            print(line)
            out.write(line + "\n")
    
    print(f"\nTotal Mapped Categories: {len(mapping)}")
    print("Mapping saved to: parallel_category_mapping.txt")

if __name__ == "__main__":
    map_urls_to_categories()
