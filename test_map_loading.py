import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path("lowes-apify-actor/src").resolve()))

def test_map():
    from main import load_lowes_map
    stores, cats = load_lowes_map()
    print(f"Total Stores: {len(stores)}")
    print(f"Total Cats: {len(cats)}")
    
    # Check if we have some WA/OR stores
    wa_stores = [s for s in stores.values() if s.get('state') == 'WA']
    or_stores = [s for s in stores.values() if s.get('state') == 'OR']
    print(f"WA Stores: {len(wa_stores)}")
    print(f"OR Stores: {len(or_stores)}")
    
    if len(cats) > 0:
        print(f"First Cat: {cats[0]}")
    if len(wa_stores) > 0:
        print(f"Example WA Store: {list(stores.items())[0]}")

if __name__ == "__main__":
    test_map()
