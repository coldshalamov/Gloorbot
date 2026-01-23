
import re

def refine_urls():
    input_file = "sitemap_minimal_structural_urls.txt"
    master_file = "master_sitemap_pl_list.txt"
    output_file = "PARALLEL/urls_refined.txt"
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Initial count: {len(urls)}")
    
    # Cleaning Step 1: Basic Filters
    clean_urls = []
    
    # Regex to find redundant facet strings (e.g., -4294967295-234234...)
    # Valid category ID usually looks like /12345678 or /4294... 
    # but faceted ones have dashes followed by more numbers usually.
    # Actually, let's just look for "simple" endings.
    
    unique_ids = set()
    kept_urls = []

    for url in urls:
        # Standardize
        url = url.lower()
        if "tesla.myloweslife.com" in url:
            continue
            
        # Parse the ID part
        # URL usually ends with /<numbers> or /<numbers>-<numbers>
        # We want to avoid deep chains like /4294...-234...-234...
        
        parts = url.split('/')
        last_segment = parts[-1]
        
        # Heuristic: If the last segment has more than 1 dash separating numbers, it's likely a complex filter
        # But wait, some canonicals might look like that.
        # Let's count the number of distinct numeric groups in the last segment.
        numeric_groups = re.findall(r'\d+', last_segment)
        
        if len(numeric_groups) > 2:
            # Likely a highly faceted URL, skip it
            continue
            
        # Store by primary ID (the first big number)
        if numeric_groups:
            primary_id = numeric_groups[0]
            if primary_id in unique_ids:
                # Duplicate base category, skip
                continue
            unique_ids.add(primary_id)
            kept_urls.append(url)
        else:
            # No ID? Keep it if it looks like a path
            kept_urls.append(url)

    print(f"After structural cleaning: {len(kept_urls)}")

    # Step 2: Ensure "Pet", "Cleaning", "Personal Care" coverage
    # We will scan the master list for these keywords if they aren't well represented
    
    keywords = ["pet", "cleaning", "personal-care", "laundry", "storage"]
    found_keywords = {k: 0 for k in keywords}
    
    for url in kept_urls:
        for k in keywords:
            if k in url:
                found_keywords[k] += 1
                
    print("Keyword coverage in refined list:")
    for k, v in found_keywords.items():
        print(f"  {k}: {v}")
        
    # If distinct low, maybe we missed them. Let's scan master list for top-level matches
    # but ONLY if they are structural (short)
    
    print(f"\nScanning {master_file} for missing high-level categories...")
    try:
        extras = []
        with open(master_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip().lower()
                
                # Check for keywords
                is_relevant = False
                for k in keywords:
                    if k in line:
                        is_relevant = True
                        break
                
                if not is_relevant:
                    continue
                    
                # Strict check for "Top Level"ness
                # Must not have too many segments
                # Must not have complex numeric endings
                parts = line.split('/')
                last_segment = parts[-1]
                numeric_groups = re.findall(r'\d+', last_segment)
                
                if len(numeric_groups) <= 1: # Strict! Only base ID or no ID
                    # Check if ID already exists
                    if numeric_groups:
                        pid = numeric_groups[0]
                        if pid not in unique_ids:
                            unique_ids.add(pid)
                            extras.append(line)
                            # print(f"  Added: {line}")
                            
        print(f"Added {len(extras)} extra high-level category URLs.")
        kept_urls.extend(extras)
        
    except Exception as e:
        print(f"Could not scan master file: {e}")

    # Final Sort
    kept_urls.sort()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# Lowe's Structural Category List\n")
        f.write(f"# Generated: {len(kept_urls)} unique high-level categories\n")
        f.write("# Optimized for scraping coverage without redundant facets\n\n")
        for u in kept_urls:
            f.write(u + "\n")
            
    print(f"Final list written to {output_file} with {len(kept_urls)} URLs.")

if __name__ == "__main__":
    refine_urls()
