def main():
    cleaned = []
    with open("master_candidate_list.txt", "r") as f:
        for line in f:
            line = line.strip()
            # Strict domain check
            if "www.lowes.com/pl/" in line:
                cleaned.append(line)
            # Fix employee links if possible, or drop them
            elif "myloweslife" in line:
                continue
                
    # Further deduping by ID just in case
    unique_map = {}
    for url in cleaned:
        # extract ID
        parts = url.split('/')
        if parts[-1].isdigit():
            cid = parts[-1]
            unique_map[cid] = url
            
    final_urls = sorted(unique_map.values())
    
    print(f"Cleaned list size: {len(final_urls)}")
    
    with open("LowesMap_Optimized_Safe.txt", "w") as f:
        for u in final_urls:
            f.write(u + "\n")

if __name__ == "__main__":
    main()
