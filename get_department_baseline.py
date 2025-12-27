import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re
import json

STORE_ID = "3240"
ROOTS = [
    "Appliances", "Bathroom", "Building-supplies", "Electrical", "Flooring", 
    "Hardware", "Heating-cooling", "Home-decor", "Kitchen", "Lawn-garden", 
    "Lighting-ceiling-fans", "Lumber-composites", "Moulding-millwork", 
    "Outdoor-living", "Paint", "Plumbing", "Smart-home-security-wi-fi", 
    "Storage-organization", "Tools", "Windows-doors"
]

async def get_root_counts():
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        results = {}
        for root in ROOTS:
            url = f"https://www.lowes.com/c/{root}?storeId={STORE_ID}&inStock=1"
            print(f"Checking {root}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)
                
                # Some /c/ pages redirect to /pl/ and show count
                # Some stay as /c/ and we need a child to get count
                count = 0
                selectors = ["[data-testid='total-results']", ".total-results", "span[class*='total-results']"]
                for sel in selectors:
                    try:
                        elem = await page.wait_for_selector(sel, timeout=3000)
                        text = await elem.inner_text()
                        nums = re.findall(r'[\d,]+', text)
                        if nums:
                            count = int(nums[-1].replace(',', ''))
                            break
                    except: continue
                
                results[root] = count
                print(f"  Count: {count}")
            except:
                results[root] = 0
                print(f"  Failed {root}")
            await asyncio.sleep(3)
            
        print("\nDEPARTMENT BASELINE SUMMARY:")
        total = 0
        for r, c in results.items():
            print(f"  {r}: {c}")
            total += c
        print(f"TOTAL ESTIMATED INVENTORY: {total}")
        
        with open("department_baseline.json", "w") as f:
            json.dump(results, f, indent=2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_root_counts())
