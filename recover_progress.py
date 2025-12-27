
import os
import re
from pathlib import Path

log_dir = Path("scrape_logs")
mapping_path = Path("LowesMap_Final_Pruned.txt")

# Load category list to find indices
with open(mapping_path, 'r') as f:
    categories = [line.strip() for line in f if '/pl/' in line]

def find_last_index(log_file):
    if not os.path.exists(log_file):
        return 0
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-2000:]  # Look at last 2000 lines
            
        # Find the last completed category name
        # Format: [INFO] Arlington, WA (#0061) - category-name: X products
        last_cat = None
        for line in reversed(lines):
            match = re.search(r' - ([^:]+): \d+ total products', line)
            if match:
                last_cat = match.group(1).strip()
                break
        
        if not last_cat:
            return 0
            
        # Find index in categories list
        for i, cat_url in enumerate(categories):
            if last_cat in cat_url:
                return i + 1  # Start at next category
                
    except Exception as e:
        print(f"Error parsing {log_file}: {e}")
    return 0

# Scan logs and create checkpoints
for log_file in log_dir.glob("worker_*.log"):
    # filename: worker_0_0061.log
    parts = log_file.stem.split('_')
    if len(parts) >= 3:
        store_id = parts[2]
        idx = find_last_index(log_file)
        if idx > 0:
            checkpoint_file = log_dir / f"checkpoint_{store_id}.txt"
            with open(checkpoint_file, 'w') as f:
                f.write(str(idx))
            print(f"Created checkpoint for {store_id} at index {idx}")

print("Recovery complete.")
