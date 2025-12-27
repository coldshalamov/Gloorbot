import asyncio
import re
import json
import os
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Akamai Avoidance Constants
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe" # Typical path
PROFILE_DIR = os.path.join(os.getcwd(), ".playwright-profiles", "audit_session")
STORE_ID = "3240"
PAGINATION_LIMIT = 2000

CHROME_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--disable-infobars',
    '--start-maximized',
]

async def human_delay(min_ms=1000, max_ms=3000):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

async def human_move(page):
    # Simulate a few mouse moves
    for _ in range(3):
        x = random.randint(100, 1000)
        y = random.randint(100, 800)
        await page.mouse.move(x, y, steps=10)
        await asyncio.sleep(random.uniform(0.1, 0.5))

async def human_scroll(page):
    # Simulate small scrolls
    for _ in range(random.randint(2, 5)):
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(0.2, 0.6))

async def get_product_count(page, url):
    # Always include store context and inStock filter for inventory check
    full_url = f"{url}?storeId={STORE_ID}&inStock=1&rollUpVariants=0"
    print(f"  [Auditing] {full_url}")
    
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
        await human_delay(2000, 4000)
        await human_move(page)
        
        # Check for block
        title = await page.title()
        if "Access Denied" in title or "Access Denied" in await page.content():
            print(f"    ❌ BLOCKED on {url}")
            return -1, []

        # Extract count
        count = 0
        selectors = [
            "[data-testid='total-results']",
            ".total-results",
            "span[class*='total-results']",
            "div[class*='resultCount']",
            "h1:has-text('Results')" # Sometimes it's in the header
        ]
        
        found_count = False
        for sel in selectors:
            try:
                elem = await page.wait_for_selector(sel, timeout=5000)
                if elem:
                    text = await elem.inner_text()
                    nums = re.findall(r'[\d,]+', text)
                    if nums:
                        count = int(nums[-1].replace(',', ''))
                        found_count = True
                        print(f"    Found count: {count}")
                        break
            except: continue
            
        # Extract direct children (if /c/ page) or sub-categories (if /pl/ page)
        # We want to find "Shop All" style links or sub-department links
        children = []
        links = await page.query_selector_all("a[href*='/pl/']")
        seen_ids = set()
        
        current_id_match = re.search(r'/(\d+)$', url)
        current_id = current_id_match.group(1) if current_id_match else None

        for link in links:
            href = await link.get_attribute("href")
            if not href: continue
            href = href.split('?')[0].rstrip('/')
            match = re.search(r'/pl/(.*?)/(\d+)$', href)
            if match:
                slug, cid = match.groups()
                if cid != current_id and cid not in seen_ids:
                    # Heuristic: Find links that look like "Shop All" or high-level containers
                    text = await link.inner_text()
                    text = text.lower()
                    
                    # We prioritize "Shop All" links if they exist
                    is_shop_all = "shop all" in text or "view all" in text
                    
                    children.append({
                        "url": href,
                        "id": cid,
                        "name": slug.replace('-', ' '),
                        "is_shop_all": is_shop_all,
                        "text": text
                    })
                    seen_ids.add(cid)
                    
        return count, children
    except Exception as e:
        print(f"    Error auditing {url}: {e}")
        return -1, []

async def resolve_minimal(page, url, results, visited):
    match = re.search(r'/(\d+)$', url)
    cid = match.group(1) if match else url
    
    if cid in visited: return
    visited.add(cid)
    
    print(f"Resolving: {url}")
    count, children = await get_product_count(page, url)
    
    if count == -1: 
        # Blocked or Error - possibly retry with new session
        return

    # If it's a listing page and it fits, we are DONE with this branch
    if "/pl/" in url:
        if count <= PAGINATION_LIMIT and count > 0:
            print(f"    ✅ BASIS FOUND: {url} ({count})")
            results.append({"url": url, "count": count, "id": cid})
            return
        elif count > PAGINATION_LIMIT:
            print(f"    ⚠️ OVER LIMIT ({count}). Must expand.")
            # If we are over limit, we MUST use children
            # Filter children: if there are "Shop All" links here, they usually point to the same count,
            # so we should ignore them and go to the more granular ones.
            granular_children = [c for c in children if not c['is_shop_all']]
            if not granular_children:
                granular_children = children
                
            for child in granular_children:
                await resolve_minimal(page, child['url'], results, visited)
            return
    else:
        # It's a /c/ page. 
        # Check if there is a "Shop All" link
        shop_all = next((c for c in children if c['is_shop_all']), None)
        if shop_all:
            print(f"    Found Shop All: {shop_all['url']}. Checking its count.")
            await resolve_minimal(page, shop_all['url'], results, visited)
        else:
            print(f"    No Shop All found for landing page. Visiting all categories.")
            for child in children:
                await resolve_minimal(page, child['url'], results, visited)

async def main():
    root_urls = [
        "https://www.lowes.com/c/Appliances",
        "https://www.lowes.com/c/Tools",
    ]
    
    final_basis = []
    visited = set()

    async with async_playwright() as p:
        # Using persistent context to store cookies and look "human"
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            args=CHROME_ARGS,
            viewport={"width": 1440, "height": 900}
        )
        
        page = context.pages[0]
        # Applied to all pages created in this context
        for p_obj in context.pages:
            await stealth_async(p_obj)
            
        print("Warming up on homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await human_delay(3000, 5000)
        await human_move(page)
        await human_scroll(page)
        
        for root in root_urls:
            print(f"\n--- AUDITING ROOT: {root} ---")
            await resolve_minimal(page, root, final_basis, visited)
            # Short break between roots
            await human_delay(5000, 10000)
            
        # Save results
        with open("minimal_basis_audit_report.json", "w") as f:
            json.dump(final_basis, f, indent=2)
            
        print(f"\nAUDIT COMPLETE. Identified {len(final_basis)} minimal basis URLs.")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
