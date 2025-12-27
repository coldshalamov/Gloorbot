import asyncio
import re
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STORE_ID = "3240" # Yakima
PAGINATION_LIMIT = 2000 
SAVE_FILE = "lowes_minimal_basis.json"

ROOT_DEPARTMENTS = [
    "Appliances", "Bathroom", "Building-supplies", "Electrical", "Flooring", 
    "Hardware", "Heating-cooling", "Home-decor", "Kitchen", "Lawn-garden", 
    "Lighting-ceiling-fans", "Lumber-composites", "Moulding-millwork", 
    "Outdoor-living", "Paint", "Plumbing", "Smart-home-security-wi-fi", 
    "Storage-organization", "Tools", "Windows-doors"
]

# Track progress
PROGRESS = {
    "roots_completed": [],
    "basis_found": [], # [{url, count, id}]
    "visited_ids": []
}

def load_progress():
    global PROGRESS
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                PROGRESS = json.load(f)
            print(f"Loaded progress: {len(PROGRESS['basis_found'])} URLs found so far.")
        except:
            pass

def save_progress():
    with open(SAVE_FILE, "w") as f:
        json.dump(PROGRESS, f, indent=2)

async def get_page_info(page, url):
    full_url = f"{url}?storeId={STORE_ID}&inStock=1&rollUpVariants=0"
    print(f"  Scoping: {full_url}")
    
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        # Determine if it's a listing page or landing page
        # Listing pages have a count
        count = 0
        is_listing = False
        
        selectors = [
            "[data-testid='total-results']",
            ".total-results",
            "span[class*='total-results']",
            "div[class*='resultCount']"
        ]
        
        for sel in selectors:
            try:
                elem = await page.wait_for_selector(sel, timeout=3000)
                if elem:
                    text = await elem.inner_text()
                    nums = re.findall(r'[\d,]+', text)
                    if nums:
                        count = int(nums[-1].replace(',', ''))
                        is_listing = True
                        print(f"    Found count: {count} with {sel}")
                        break
            except: continue

        # Get sub-category links (children)
        # We look for /pl/ links that are NOT the current ID
        current_id_match = re.search(r'/(\d+)$', url)
        current_id = current_id_match.group(1) if current_id_match else None
        
        child_links = []
        # Main content tiles and sidebar links
        elements = await page.query_selector_all("a[href*='/pl/']")
        for el in elements:
            href = await el.get_attribute("href")
            if not href: continue
            href = href.split('?')[0].rstrip('/')
            match = re.search(r'/pl/(.*?)/(\d+)$', href)
            if match:
                cid = match.group(2)
                if cid != current_id:
                    if href not in child_links:
                        child_links.append(href)
        
        return is_listing, count, child_links
    except Exception as e:
        print(f"    Error on {url}: {e}")
        return False, 0, []

async def crawl(page, url):
    match = re.search(r'/(\d+)$', url)
    if not match: return
    cid = match.group(1)
    
    if cid in PROGRESS["visited_ids"]: return
    PROGRESS["visited_ids"].append(cid)
    
    print(f"Crawl: {url}")
    is_listing, count, children = await get_page_info(page, url)
    
    if is_listing:
        if count <= PAGINATION_LIMIT and count > 0:
            print(f"    ✅ ADDING BASIS: {url} ({count})")
            PROGRESS["basis_found"].append({"url": url, "count": count, "id": cid})
            save_progress()
        elif count > PAGINATION_LIMIT:
            print(f"    ⚠️ OVERFLOW ({count}). Hubbing to {len(children)} children.")
            for child in children:
                await crawl(page, child)
        else:
            print(f"    Empty listing. Skipping.")
    else:
        # Landing page (/c/ or /pl/ hub)
        print(f"    Landing page. Hubbing to {len(children)} children.")
        for child in children:
            await crawl(page, child)

async def main():
    load_progress()
    
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        for i in range(0, len(ROOT_DEPARTMENTS), 1):
            root = ROOT_DEPARTMENTS[i]
            if root in PROGRESS["roots_completed"]:
                continue
            
            print(f"\nROOT DEPARTMENT: {root}")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Go to root
                await page.goto(f"https://www.lowes.com/c/{root}", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)
                # Redirect check
                current_url = page.url.split('?')[0].rstrip('/')
                if "/pl/" in current_url:
                    await crawl(page, current_url)
                else:
                    # If it's still a /c/ page, manual extract children
                    _, _, children = await get_page_info(page, f"https://www.lowes.com/c/{root}")
                    for child in children:
                        await crawl(page, child)
                
                PROGRESS["roots_completed"].append(root)
                save_progress()
            except Exception as e:
                print(f"  Fatal error on root {root}: {e}")
            
            await browser.close()
            await asyncio.sleep(10) # Heavy throttle to avoid block

    print(f"COMPLETED. Basis size: {len(PROGRESS['basis_found'])}")

if __name__ == "__main__":
    asyncio.run(main())
