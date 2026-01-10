
import sys
from pathlib import Path
from collections import Counter

def parse_lowes_url(url):
    """
    Extracts the path and ID from a Lowe's PL URL.
    Example: https://www.lowes.com/pl/Category-Name/NumericID
    Returns (path, id)
    """
    url = url.strip()
    if not url or '/pl/' not in url:
        return None, None
    
    parts = url.split('/pl/')
    if len(parts) < 2:
        return None, None
    
    path_and_id = parts[1].split('?')[0].rstrip('/')
    path_parts = path_and_id.split('/')
    
    if len(path_parts) >= 2:
        # Last part is usually the ID
        category_id = path_parts[-1]
        category_path = "/".join(path_parts[:-1])
        return category_path, category_id
    elif len(path_parts) == 1:
        # Just a name or just an ID? 
        # Usually it's Name-with-ID-at-end
        return path_parts[0], None
    
    return None, None

def main():
    urls_file = Path("PARALLEL/urls.txt")
    sitemap_file = Path("master_sitemap_pl_list.txt")
    
    if not urls_file.exists():
        print(f"Error: {urls_file} not found")
        return
    
    if not sitemap_file.exists():
        print(f"Error: {sitemap_file} not found")
        return

    print(f"Loading our URLs from {urls_file}...")
    our_paths = set()
    our_ids = set()
    with open(urls_file, 'r', encoding='utf-8') as f:
        for line in f:
            path, cid = parse_lowes_url(line)
            if path:
                our_paths.add(path)
            if cid:
                our_ids.add(cid)
    
    print(f"Found {len(our_paths)} unique category paths and {len(our_ids)} unique IDs in our list.")

    print(f"Analyzing sitemap from {sitemap_file} (this may take a moment)...")
    sitemap_path_counts = Counter()
    sitemap_top_level = Counter()
    total_sitemap_urls = 0
    
    # Process sitemap line by line to be memory efficient
    with open(sitemap_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_sitemap_urls += 1
            path, cid = parse_lowes_url(line)
            if path:
                sitemap_path_counts[path] += 1
                top_level = path.split('/')[0]
                sitemap_top_level[top_level] += 1
            
            if total_sitemap_urls % 100000 == 0:
                print(f"  Processed {total_sitemap_urls} URLs...")

    print(f"\nSitemap Summary:")
    print(f"Total Sitemap PL URLs: {total_sitemap_urls}")
    print(f"Total Unique Paths in Sitemap: {len(sitemap_path_counts)}")
    print(f"Total Top-Level Departments in Sitemap: {len(sitemap_top_level)}")

    # Coverage analysis
    covered_sitemap_urls = 0
    for path in our_paths:
        covered_sitemap_urls += sitemap_path_counts.get(path, 0)
    
    print(f"\nCoverage Results:")
    print(f"Sitemap URLs covered by our paths: {covered_sitemap_urls} ({covered_sitemap_urls/total_sitemap_urls*100:.2f}%)")
    
    # Missing Departments
    our_top_levels = set(p.split('/')[0] for p in our_paths)
    missing_top_levels = set(sitemap_top_level.keys()) - our_top_levels
    
    print(f"\nDepartments in Sitemap MISSING from our list ({len(missing_top_levels)}):")
    for dept in sorted(list(missing_top_levels)):
        count = sitemap_top_level[dept]
        print(f"  - {dept} ({count} URLs)")

    # Largest covered departments
    print(f"\nTop 10 Departments WE ARE CRAWLING:")
    covered_depts = Counter()
    for path in our_paths:
        tl = path.split('/')[0]
        covered_depts[tl] += sitemap_path_counts.get(path, 0)
    
    for dept, count in covered_depts.most_common(10):
        print(f"  - {dept}: {count} URLs")

    # Save detailed report
    with open("category_audit_results.txt", "w", encoding='utf-8') as f:
        f.write("# Lowe's Category Audit Report\n\n")
        f.write(f"Source URLs: {urls_file}\n")
        f.write(f"Sitemap Source: {sitemap_file}\n\n")
        f.write(f"Total Sitemap PL URLs: {total_sitemap_urls}\n")
        f.write(f"Our Coverage: {covered_sitemap_urls} URLs ({covered_sitemap_urls/total_sitemap_urls*100:.2f}%)\n\n")
        
        f.write("## Departments Missing Entirely\n")
        for dept in sorted(list(missing_top_levels)):
            f.write(f"- {dept} ({sitemap_top_level[dept]} URLs)\n")
        
        f.write("\n## Our Current Departments (Top-Level)\n")
        for dept, count in covered_depts.most_common():
            f.write(f"- {dept}: {count} URLs\n")

    print("\n✅ Audit complete. Results saved to category_audit_results.txt")

if __name__ == "__main__":
    main()
