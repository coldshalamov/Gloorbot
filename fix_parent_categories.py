# Script to FIX parent category URLs by adding ?goToProdList=true
# This forces Lowe's to show product listings instead of category landing pages

import re
from pathlib import Path

def is_parent_category(url: str) -> bool:
    """Check if a URL is a parent category (1 segment = shows landing page)"""
    match = re.search(r'/pl/([^?]+)', url)
    if not match:
        return False
    path = match.group(1)
    segments = [s for s in path.split('/') if s and not s.isdigit()]
    return len(segments) <= 1

def fix_url(url: str) -> str:
    """Add ?goToProdList=true to parent category URLs"""
    url = url.strip()
    if not is_parent_category(url):
        return url
    
    # Check if already has query params
    if '?' in url:
        if 'goToProdList=true' not in url:
            return url + '&goToProdList=true'
        return url
    else:
        return url + '?goToProdList=true'

def fix_file(path: Path) -> tuple[int, int]:
    """Fix parent category URLs in a file. Returns (fixed, total)."""
    if not path.exists():
        return (0, 0)
    
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    fixed_lines = []
    fixed_count = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        
        if '/pl/' in stripped and is_parent_category(stripped):
            new_url = fix_url(stripped)
            if new_url != stripped:
                print(f"  FIX: {stripped[:60]}...")
                print(f"    → {new_url[:60]}...")
                fixed_count += 1
            fixed_lines.append(new_url)
        else:
            fixed_lines.append(line)
    
    # Preview only - don't write yet
    return (fixed_count, len([l for l in fixed_lines if l.strip() and not l.strip().startswith('#')]))

# Files to check
files = [
    Path("apps/coordinator/data/urls.txt"),
    Path("PARALLEL/urls.txt"),
    Path("LowesMap.txt"),
    Path("new_categories.txt"),
]

print("=== PREVIEW: Adding ?goToProdList=true to parent category URLs ===")
print("This forces Lowe's to show product listings instead of landing pages\n")

total_fixed = 0
for f in files:
    print(f"\n{f}:")
    fixed, total = fix_file(f)
    total_fixed += fixed
    print(f"  Would fix: {fixed} of {total} URLs")

print(f"\n=== TOTAL TO FIX: {total_fixed} ===")
print("\nThis is a PREVIEW. Run with --apply to make changes.")
