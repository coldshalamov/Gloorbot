import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import json

DEPARTMENTS = [
    "Appliances", "Bathroom", "Building Supplies", "Electrical", "Flooring", 
    "Hardware", "Heating & Cooling", "Home Decor", "Kitchen", "Lawn & Garden", 
    "Lighting & Ceiling Fans", "Lumber & Composites", "Moulding & Millwork", 
    "Outdoor Living", "Paint", "Plumbing", "Smart Home & Security", 
    "Storage & Organization", "Tools", "Windows & Doors"
]

async def get_root_pl_urls():
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        # Click "Shop" or "Departments"
        try:
            await page.click("button:has-text('Shop')", timeout=5000)
            await asyncio.sleep(2)
        except: pass
        
        roots = {} # Name -> pl_url
        
        # Get all links in the menu that have /pl/ and "View All" or "Shop All"
        links = await page.query_selector_all("a[href*='/pl/']")
        for link in links:
            text = await link.inner_text()
            href = await link.get_attribute("href")
            if "Shop All" in text or "View All" in text:
                # Associate with department based on text or parent
                print(f"Found root-like link: {text} -> {href}")
                roots[text] = href
                
        with open("potential_root_urls.json", "w") as f:
            json.dump(roots, f, indent=2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_root_pl_urls())
