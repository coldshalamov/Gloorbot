# Script to REMOVE parent category URLs from all seed files
# These URLs redirect to /c/ pages and cause infinite scraper retries

import re
from pathlib import Path

def is_parent_category(url: str) -> bool:
    """Check if a URL is a parent category (1 segment = redirects to /c/)"""
    match = re.search(r'/pl/([^?]+)', url)
    if not match:
        return False
    path = match.group(1)
    segments = [s for s in path.split('/') if s and not s.isdigit()]
    return len(segments) <= 1

def clean_file(path: Path) -> tuple[int, int]:
    """Remove parent category URLs from a file. Returns (removed, kept)."""
    if not path.exists():
        return (0, 0)
    
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    kept = []
    removed = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            kept.append(line)
            continue
        
        if '/pl/' in stripped and is_parent_category(stripped):
            removed += 1
            print(f"  REMOVING: {stripped[:80]}...")
        else:
            kept.append(line)
    
    if removed > 0:
        path.write_text('\n'.join(kept) + '\n', encoding='utf-8')
    
    return (removed, len([l for l in kept if l.strip() and not l.strip().startswith('#')]))

# Files to clean
files = [
    Path("apps/coordinator/data/urls.txt"),
    Path("PARALLEL/urls.txt"),
    Path("LowesMap.txt"),
    Path("new_categories.txt"),
]

print("=== REMOVING PARENT CATEGORY URLs ===")
print("These redirect to /c/ pages and break the scraper\n")

total_removed = 0
for f in files:
    print(f"\n{f}:")
    removed, kept = clean_file(f)
    total_removed += removed
    print(f"  Removed: {removed}, Kept: {kept}")

print(f"\n=== TOTAL REMOVED: {total_removed} ===")
print("\nDon't forget to:")
print("1. Commit and push changes")
print("2. Redeploy the coordinator on Render")
print("3. Rebuild the worker installer")
