import asyncio
import json
import re
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STORE_ID = "3240"
PAGINATION_LIMIT = 2000
MASTER_FILE = "master_candidate_ids.json"
FINAL_SAVE = "autonomous_basis_discovery.json"

async def get_count(page, url):
    full_url = f"{url}?storeId={STORE_ID}&inStock=1&rollUpVariants=0"
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        
        # Check for Access Denied
        if "Access Denied" in await page.content():
            print(f"      !!! ACCESS DENIED for {url}")
            return -1 
            
        selectors = [
            "[data-testid='total-results']",
            ".total-results",
            "span[class*='total-results']",
            "div[class*='resultCount']",
            "h1:has-text('results')"
        ]
        
        for sel in selectors:
            try:
                elem = await page.wait_for_selector(sel, timeout=3000)
                text = await elem.inner_text()
                nums = re.findall(r'[\d,]+', text)
                if nums:
                    return int(nums[-1].replace(',', ''))
            except: continue
        return 0
    except Exception as e:
        print(f"      Error: {e}")
        return 0

async def main():
    if not os.path.exists(MASTER_FILE):
        print("Master file missing.")
        return
        
    with open(MASTER_FILE, "r") as f:
        master = json.load(f) # id -> url
        
    # Categorize by their path depth
    # We want to visit shallow ones first
    sorted_ids = sorted(master.keys(), key=lambda x: master[x].count('/'))
    
    basis = []
    processed_count = 0
    
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Track coverage
        # If we take a parent, we don't need its children.
        # How do we know which are children? 
        # For this script, we'll use string prefix matching on the URL path.
        
        final_selected_ids = []
        covered_ids = set()
        
        for cid in sorted_ids:
            if cid in covered_ids: continue
            
            url = master[cid]
            print(f"Auditing [{processed_count}/{len(master)}]: {url}")
            
            count = await get_count(page, url)
            processed_count += 1
            
            if count == -1:
                # Blocked. Rotate context?
                print("    Blocked. Restarting browser...")
                await browser.close()
                await asyncio.sleep(20)
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                continue
                
            if count > 0 and count <= PAGINATION_LIMIT:
                print(f"    ✅ BASIS FOUND: {url} ({count} items)")
                basis.append({"url": url, "count": count, "id": cid})
                final_selected_ids.append(cid)
                
                # Mark potential children as covered (optimization)
                # This only works if we trust the hierarchy in the URL path
                path_part = url.split('/pl/')[1].split('?')[0].rstrip('/') if '/pl/' in url else None
                if path_part:
                    for other_cid, other_url in master.items():
                        if other_cid == cid: continue
                        if path_part + "/" in other_url:
                            covered_ids.add(other_cid)
            elif count > PAGINATION_LIMIT:
                print(f"    ⚠️ OVERFLOW ({count}). Moving to children...")
                # We don't add this parent, we let the loop pick up its children later
            else:
                print(f"    Empty or Hub. Skipping.")
                
            # Periodically save
            if processed_count % 10 == 0:
                with open(FINAL_SAVE, "w") as f:
                    json.dump(basis, f, indent=2)
                    
        await browser.close()

    print(f"Discovery Complete. Basis size: {len(basis)}")
    with open("LowesMap_EXHAUSTIVE.txt", "w") as f:
        for b in basis:
            f.write(b['url'] + "\n")

if __name__ == "__main__":
    asyncio.run(main())
