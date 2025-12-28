import json
import os
from pathlib import Path

output_dir = Path("output")
files = list(output_dir.glob("*.jsonl"))

print("=" * 70)
print("SCRAPER DIAGNOSTIC REPORT")
print("=" * 70)
print()

total_products = 0
worker_stats = []

for file in sorted(files):
    # Count lines
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        count = len(lines)
        total_products += count
    
    # Get file size
    size_mb = file.stat().st_size / (1024 * 1024)
    
    # Extract worker info from filename
    worker_name = file.stem
    
    # Sample first and last product
    first_product = None
    last_product = None
    
    if lines:
        try:
            first_product = json.loads(lines[0])
            last_product = json.loads(lines[-1])
        except:
            pass
    
    worker_stats.append({
        'file': file.name,
        'worker': worker_name,
        'products': count,
        'size_mb': round(size_mb, 2),
        'first_product': first_product.get('title', 'N/A')[:50] if first_product else 'N/A',
        'last_product': last_product.get('title', 'N/A')[:50] if last_product else 'N/A',
        'store_id': first_product.get('store_id', 'N/A') if first_product else 'N/A',
        'store_name': first_product.get('store_name', 'N/A') if first_product else 'N/A'
    })

# Print summary
for stat in worker_stats:
    print(f"Worker: {stat['worker']}")
    print(f"  Store: {stat['store_name']} (#{stat['store_id']})")
    print(f"  Products: {stat['products']:,}")
    print(f"  File Size: {stat['size_mb']} MB")
    print(f"  First: {stat['first_product']}")
    print(f"  Last: {stat['last_product']}")
    print()

print("=" * 70)
print(f"TOTAL PRODUCTS SCRAPED: {total_products:,}")
print(f"TOTAL FILES: {len(files)}")
print(f"AVERAGE PER WORKER: {total_products // len(files) if files else 0:,}")
print("=" * 70)

# Check for duplicates
print("\nChecking for duplicate products...")
all_urls = set()
duplicates = 0

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                product = json.loads(line)
                url = product.get('url', '')
                if url in all_urls:
                    duplicates += 1
                else:
                    all_urls.add(url)
            except:
                pass

print(f"Unique Products: {len(all_urls):,}")
print(f"Duplicate Products: {duplicates:,}")
print(f"Deduplication Rate: {(1 - duplicates/total_products)*100:.1f}%" if total_products > 0 else "N/A")
