"""
Analyze parallel test output to determine:
1. Which categories were actually scraped
2. How far each worker got before being blocked
3. Whether categories are being rerun or duplicated
"""

import json
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

def extract_category_from_product_url(product_url):
    """
    Product URLs are like: https://www.lowes.com/pd/Product-Name/12345
    These don't tell us which category they came from, but we can track
    products appearing in multiple workers to detect overlap.
    """
    return product_url

def extract_product_id(product_url):
    """Extract the numeric product ID from the URL"""
    parts = product_url.rstrip('/').split('/')
    if parts[-1].isdigit():
        return parts[-1]
    return None

def analyze_worker_output(filepath):
    """Read a worker output file and extract metadata"""
    products = []
    product_ids = set()
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                product = json.loads(line)
                products.append(product)
                
                product_id = extract_product_id(product.get('url', ''))
                if product_id:
                    product_ids.add(product_id)
                    
            except json.JSONDecodeError:
                print(f"  [WARN] Invalid JSON at line {line_num}")
                continue
    
    return products, product_ids

# Analyze all workers
output_dir = Path('scrape_output_parallel')
workers = {}

for jsonl_file in sorted(output_dir.glob('worker_*.jsonl')):
    worker_name = jsonl_file.stem
    print(f"\nAnalyzing {worker_name}...")
    
    products, product_ids = analyze_worker_output(jsonl_file)
    workers[worker_name] = {
        'total_products': len(products),
        'unique_product_ids': len(product_ids),
        'product_ids': product_ids,
        'products': products,
        'first_product': products[0] if products else None,
        'last_product': products[-1] if products else None,
    }
    
    print(f"  Total product entries: {len(products)}")
    print(f"  Unique product IDs: {len(product_ids)}")
    if products:
        print(f"  First scrape: {products[0]['scraped_at']}")
        print(f"  Last scrape: {products[-1]['scraped_at']}")
        print(f"  First product: {products[0]['title'][:50]}...")
        print(f"  Last product: {products[-1]['title'][:50]}...")

# Analysis results
print("\n" + "="*70)
print("CROSS-WORKER ANALYSIS")
print("="*70)

# Find product overlap between workers
all_product_ids = set()
product_to_workers = defaultdict(set)

for worker_name, data in workers.items():
    for product_id in data['product_ids']:
        product_to_workers[product_id].add(worker_name)
        all_product_ids.add(product_id)

# Count overlaps
overlap_count = sum(1 for prod_id, worker_set in product_to_workers.items() if len(worker_set) > 1)
single_worker = sum(1 for prod_id, worker_set in product_to_workers.items() if len(worker_set) == 1)

print(f"\nTotal unique product IDs across all workers: {len(all_product_ids)}")
print(f"Products in MULTIPLE workers (overlap): {overlap_count}")
print(f"Products in SINGLE worker only: {single_worker}")

if len(all_product_ids) > 0:
    overlap_pct = overlap_count / len(all_product_ids) * 100
    print(f"Overlap rate: {overlap_pct:.1f}%")

# Show most overlapped products
print("\nMost overlapped products (appear in multiple workers):")
sorted_overlap = sorted(product_to_workers.items(), 
                       key=lambda x: len(x[1]), 
                       reverse=True)[:10]

for product_id, worker_set in sorted_overlap:
    if len(worker_set) > 1:
        workers_list = ', '.join(sorted(worker_set))
        print(f"  Product {product_id}: in {len(worker_set)} workers ({workers_list})")

# Estimate duplication
print("\n" + "="*70)
print("DUPLICATION ANALYSIS")
print("="*70)

total_entries = sum(data['total_products'] for data in workers.values())
print(f"\nTotal product entries across all workers: {total_entries}")
print(f"Unique product IDs: {len(all_product_ids)}")
print(f"Duplication rate: {(1 - len(all_product_ids)/total_entries)*100:.1f}%")

# Per-worker breakdown
print("\nPer-worker breakdown:")
for worker_name in sorted(workers.keys()):
    data = workers[worker_name]
    store_info = data['first_product']
    if store_info:
        store = store_info['store_name']
        entries = data['total_products']
        unique = data['unique_product_ids']
        dup_rate = (1 - unique/entries)*100 if entries > 0 else 0
        print(f"  {worker_name} ({store}): {entries} entries, {unique} unique, {dup_rate:.1f}% duplication")

# Category coverage estimate
print("\n" + "="*70)
print("CATEGORY COVERAGE ESTIMATE")
print("="*70)

# If we assume ~30 products per category page on average
avg_products_per_category = 30

for worker_name in sorted(workers.keys()):
    data = workers[worker_name]
    unique_ids = data['unique_product_ids']
    estimated_categories = unique_ids / avg_products_per_category
    print(f"{worker_name}: ~{estimated_categories:.0f} categories covered (estimated from {unique_ids} unique products)")

print("\n" + "="*70)
print("KEY INSIGHTS")
print("="*70)

print("""
1. OVERLAP ANALYSIS:
   - If overlap is <10%: Categories are mostly distinct - each worker scraped different categories
   - If overlap is 20-50%: Some categories rerun or overlapping product sets
   - If overlap is >50%: Workers are scraping same categories repeatedly

2. DUPLICATION WITHIN WORKERS:
   - Duplication = (total_entries - unique_ids) / total_entries
   - High duplication could mean:
     a) Products appearing on multiple pages of same category
     b) Same products in multiple categories (category overlap)
     c) Worker restarting and re-scraping same category

3. PROGRESS ESTIMATE:
   - Each worker scraped ~{} entries
   - If each category has ~30 products per page
   - With ~515 categories and ~2-3 pages per category = ~30k-46k products expected
   - Actual: {} products average per worker
""".format(total_entries // len(workers), total_entries // len(workers)))

print(f"\nConclusion:")
if overlap_count / len(all_product_ids) < 0.15:
    print("  [+] LOW OVERLAP: Workers scraped different categories successfully")
    print("      No significant category rerunning detected")
    print("      Categories are mostly distinct (good sign)")
else:
    print(f"  [!] SIGNIFICANT OVERLAP ({overlap_pct:.1f}%): Categories may be overlapping or")
    print("      workers may be restarting and re-scraping same categories")
