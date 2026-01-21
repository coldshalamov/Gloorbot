"""
Debug script to check what paths exist on Render.
Add this as a temporary endpoint to see the actual directory structure.
"""
from pathlib import Path
import os

print("=" * 70)
print("DIRECTORY STRUCTURE DEBUG")
print("=" * 70)

# Current file location
current = Path(__file__).resolve()
print(f"\nCurrent file: {current}")
print(f"Parent 0 (same dir): {current.parent}")
print(f"Parent 1: {current.parent.parent}")
print(f"Parent 2: {current.parent.parent.parent}")
try:
    print(f"Parent 3: {current.parent.parent.parent.parent}")
except:
    print("Parent 3: (doesn't exist)")

# Check common locations
print("\n" + "=" * 70)
print("CHECKING COMMON PATHS")
print("=" * 70)

paths_to_check = [
    "/app/PARALLEL/urls.txt",
    "./PARALLEL/urls.txt",
    Path(__file__).resolve().parent / "PARALLEL" / "urls.txt",
    Path(__file__).resolve().parent.parent / "PARALLEL" / "urls.txt",
    Path(__file__).resolve().parent.parent.parent / "PARALLEL" / "urls.txt",
]

try:
    paths_to_check.append(Path(__file__).resolve().parent.parent.parent.parent / "PARALLEL" / "urls.txt")
except:
    pass

for p in paths_to_check:
    exists = Path(p).exists()
    print(f"{'✅' if exists else '❌'} {p}")

# List what's actually in /app
print("\n" + "=" * 70)
print("CONTENTS OF /app")
print("=" * 70)
if Path("/app").exists():
    for item in Path("/app").iterdir():
        print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
