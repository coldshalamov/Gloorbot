
from pathlib import Path

pruned_path = Path("LowesMap_Final_Pruned.txt")
map_path = Path("LowesMap.txt")

with open(map_path, 'r') as f:
    stores = [line.strip() for line in f if '/store/' in line]

with open(pruned_path, 'a') as f:
    f.write("\n# STORES\n")
    for store in stores:
        f.write(store + "\n")

print(f"Appended {len(stores)} stores to {pruned_path}")
