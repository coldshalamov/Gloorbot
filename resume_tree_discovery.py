import asyncio
import json
import re
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Remaining departments to discover
REMAINING_DEPARTMENTS = [
    "Lighting-ceiling-fans", "Lumber-composites", "Moulding-millwork", 
    "Outdoor-living", "Paint", "Plumbing", "Smart-home-security-wi-fi", 
    "Storage-organization", "Tools", "Windows-doors"
]

JSON_FILE = "site_tree_discovery.json"

async def discover_categories(page, root_name):
    url = f"https://www.lowes.com/c/{root_name}"
    print(f"Discovering categories from: {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        links = await page.eval_on_selector_all("a[href*='/pl/']", "elements => elements.map(e => ({href: e.href, text: e.innerText}))")
        
        discovered = []
        for link in links:
            href = link['href'].split('?')[0].rstrip('/')
            match = re.search(r'/pl/(.*?)/(\d+)', href)
            if match:
                discovered.append({
                    "name": link['text'].strip(),
                    "url": href,
                    "id": match.group(2),
                    "path": match.group(1),
                    "parent": root_name
                })
        
        print(f"  Found {len(discovered)} potential sub-categories for {root_name}")
        return discovered
    except Exception as e:
        print(f"  Error discovering {root_name}: {e}")
        return None # Indicate failure to retry later or skip

async def main():
    # Load existing data
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            all_discovered = json.load(f)
        print(f"Loaded {len(all_discovered)} existing categories.")
    else:
        all_discovered = {}

    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        # New strategy: One context per 3 departments to avoid crashes
        for i in range(0, len(REMAINING_DEPARTMENTS), 3):
            batch = REMAINING_DEPARTMENTS[i:i+3]
            print(f"\nStarting batch: {batch}")
            
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            for root in batch:
                cats = await discover_categories(page, root)
                if cats is not None:
                    for cat in cats:
                        if cat['id'] not in all_discovered:
                            all_discovered[cat['id']] = cat
                    
                    # Incremental save
                    with open(JSON_FILE, "w") as f:
                        json.dump(all_discovered, f, indent=2)
                
                await asyncio.sleep(3)
            
            await browser.close()
            print(f"Batch completed. Total unique: {len(all_discovered)}")
            await asyncio.sleep(2)

    print(f"\nFINAL TOTAL UNIQUE CATEGORIES: {len(all_discovered)}")

if __name__ == "__main__":
    asyncio.run(main())
