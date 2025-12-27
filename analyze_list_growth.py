import json

def normalize(url):
    return url.strip().split('?')[0]

def main():
    # Load User's Original List
    user_urls = set()
    try:
        with open("LowesMap.txt", "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    user_urls.add(normalize(line))
    except:
        print("Could not load LowesMap.txt")
        return

    # Load Optimzed List
    opt_urls = set()
    try:
        with open("LowesMap_Optimized_Safe.txt", "r") as f:
            for line in f:
                if line.strip():
                    opt_urls.add(normalize(line))
    except:
        print("Could not load Optimized list")
        return

    # Analyze
    new_urls = opt_urls - user_urls
    dropped_urls = user_urls - opt_urls # Should be 0 or close to 0 (unless cleaned)

    print(f"User Original Count: {len(user_urls)}")
    print(f"Optimized List Count: {len(opt_urls)}")
    print(f"New URLs Added: {len(new_urls)}")
    
    # Check Hierarchy of New URLs
    # Are they children of User URLs?
    child_expansion = 0
    brand_new = 0
    
    user_paths = [u.split('/pl/')[-1] for u in user_urls if '/pl/' in u]
    
    sample_expansions = []
    
    for new_u in new_urls:
        if '/pl/' not in new_u: continue
        new_path = new_u.split('/pl/')[-1]
        
        is_child = False
        for upath in user_paths:
            # Simple substring check (imperfect but indicative)
            # Check if upath is a prefix of new_path
            if new_path.startswith(upath + "/"):
                is_child = True
                if len(sample_expansions) < 5:
                    sample_expansions.append(f"Expanded '{upath}' -> '{new_path}'")
                break
        
        if is_child:
            child_expansion += 1
        else:
            brand_new += 1

    print(f"\nAnalysis of {len(new_urls)} New URLs:")
    print(f"  Sub-category Expansions (Deepening): {child_expansion}")
    print(f"  Brand New Departments (Widening): {brand_new}")
    
    if sample_expansions:
        print("\nExamples of Expansion (Necessary for Pagination Limits):")
        for s in sample_expansions:
            print(f"  - {s}")

if __name__ == "__main__":
    main()
