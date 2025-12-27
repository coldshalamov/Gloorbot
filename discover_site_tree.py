import asyncio
import json
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Root departments to start discovery
ROOT_DEPARTMENTS = [
    "Appliances", "Bathroom", "Building-supplies", "Electrical", "Flooring", 
    "Hardware", "Heating-cooling", "Home-decor", "Kitchen", "Lawn-garden", 
    "Lighting-ceiling-fans", "Lumber-composites", "Moulding-millwork", 
    "Outdoor-living", "Paint", "Plumbing", "Smart-home-security-wi-fi", 
    "Storage-organization", "Tools", "Windows-doors"
]

async def discover_categories(page, root_name):
    url = f"https://www.lowes.com/c/{root_name}"
    print(f"Discovering categories from: {url}")
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        # Look for category links. They often have /pl/ in the href.
        # 1. Grid of categories in the main content
        # 2. Sidebar filters
        
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
        return []

async def main():
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        all_discovered = {}
        
        for root in ROOT_DEPARTMENTS:
            cats = await discover_categories(page, root)
            for cat in cats:
                if cat['id'] not in all_discovered:
                    all_discovered[cat['id']] = cat
            await asyncio.sleep(2) # Throttle
            
        print(f"\nTOTAL UNIQUE CATEGORIES FOUND: {len(all_discovered)}")
        
        with open("site_tree_discovery.json", "w") as f:
            json.dump(all_discovered, f, indent=2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
