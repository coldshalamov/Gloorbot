import asyncio
import re
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STORE_ID = "3240" # Yakima
PAGINATION_LIMIT = 2000 # Safety margin (UI usually stops at 2400-5000)

ROOT_DEPARTMENTS = [
    "Appliances", "Bathroom", "Building-supplies", "Electrical", "Flooring", 
    "Hardware", "Heating-cooling", "Home-decor", "Kitchen", "Lawn-garden", 
    "Lighting-ceiling-fans", "Lumber-composites", "Moulding-millwork", 
    "Outdoor-living", "Paint", "Plumbing", "Smart-home-security-wi-fi", 
    "Storage-organization", "Tools", "Windows-doors"
]

async def get_count_and_children(page, url):
    full_url = f"{url}?storeId={STORE_ID}&inStock=1&rollUpVariants=0"
    print(f"  Checking: {full_url}")
    
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        
        # 1. Get Count
        count = 0
        try:
            # Try result count selector
            count_elem = await page.wait_for_selector("span[class*='result-count'], div[class*='resultCount'], h1:has-text('Results')", timeout=5000)
            text = await count_elem.inner_text()
            nums = re.findall(r'[\d,]+', text)
            if nums:
                count = int(nums[-1].replace(',', ''))
        except:
            # Fallback for pages that might not show count easily
            pass
            
        # 2. Get Children (links to other /pl/ pages on THIS page)
        child_links = []
        try:
            # Look for sub-category chips or sidebar links
            # Typically in a [data-testid='category-grid'] or similar
            elements = await page.query_selector_all("a[href*='/pl/']")
            for el in elements:
                href = await el.get_attribute("href")
                if not href: continue
                href = href.split('?')[0].rstrip('/')
                
                # Deduplicate and validate
                if "/pl/" in href and href != url.rstrip('/'):
                    # Check if it's a child (path is longer or has more slashes)
                    if href not in child_links:
                        child_links.append(href)
        except:
            pass
            
        return count, child_links
    except Exception as e:
        print(f"    Error: {e}")
        return 0, []

async def crawl(page, url, results_list, visited_ids):
    # Extract ID
    match = re.search(r'/(\d+)$', url)
    if not match: return
    cid = match.group(1)
    
    if cid in visited_ids: return
    visited_ids.add(cid)
    
    count, children = await get_count_and_children(page, url)
    print(f"    Count: {count}")
    
    if count == 0:
        # Might be a landing page with zero products directly but many sub-categories
        print("    No items found directly. Recursing into children.")
        for child in children:
            await crawl(page, child, results_list, visited_ids)
    elif count <= PAGINATION_LIMIT:
        # Everything fits! This is a "Minimal Basis" URL.
        print(f"    ✅ ADDING: {url} ({count} items)")
        results_list.append({"url": url, "count": count, "id": cid})
    else:
        # Too many items. Must drill down.
        print(f"    ⚠️ OVERFLOW ({count} > {PAGINATION_LIMIT}). Drilling down...")
        if children:
            for child in children:
                await crawl(page, child, results_list, visited_ids)
        else:
            # No children found but overflowed? We have to keep it as a fallback
            print(f"    ❌ NO CHILDREN FOUND for overflowed category. Keeping parent as best effort.")
            results_list.append({"url": url, "count": count, "id": cid})

async def main():
    final_list = []
    visited_ids = set()

    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        # Batching roots to avoid browser bloat/crashes
        for i in range(0, len(ROOT_DEPARTMENTS), 2):
            batch = ROOT_DEPARTMENTS[i:i+2]
            print(f"\n--- STARTING BATCH: {batch} ---")
            
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            for root in batch:
                root_url = f"https://www.lowes.com/c/{root}"
                print(f"\nROOT: {root}")
                try:
                    await page.goto(root_url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(4)
                    if "/pl/" in page.url:
                        pl_url = page.url.split('?')[0].rstrip('/')
                        await crawl(page, pl_url, final_list, visited_ids)
                except Exception as e:
                    print(f"  Failed root {root}: {e}")
                
                # Incremental save during batch
                with open("minimal_basis_urls_partial.json", "w") as f:
                    json.dump(final_list, f, indent=2)
            
            await browser.close()
            print(f"--- BATCH COMPLETED. Result count: {len(final_list)} ---")
            await asyncio.sleep(5)
                
        print(f"\nFINAL MINIMAL BASIS FOUND: {len(final_list)} URLs")
        
        with open("minimal_basis_urls.json", "w") as f:
            json.dump(final_list, f, indent=2)
            
        # Output as txt for scraper
        with open("LowesMap_Optimized.txt", "w") as f:
            for item in final_list:
                f.write(f"{item['url']}\n")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
