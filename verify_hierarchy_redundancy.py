import asyncio
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def get_count(page, url, store_id):
    # Lowe's URLs often need storeId and inStock params to show local counts
    full_url = f"{url}?storeId={store_id}&inStock=1&rollUpVariants=0"
    print(f"Checking: {full_url}")
    
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
        # Pacing
        await asyncio.sleep(3)
        
        # Look for count text
        # Common selectors for Lowe's results count:
        # span[class*='result-count']
        # div[class*='results-count']
        # h1[class*='results-title']
        
        selectors = [
            "span:near(h1):has-text('Results')",
            "div[class*='resultCount']",
            "span[class*='result-count']",
            "h1" # Sometimes it's in the H1 like "1,234 Results for ..."
        ]
        
        count = 0
        for sel in selectors:
            try:
                elem = await page.wait_for_selector(sel, timeout=5000)
                text = await elem.inner_text()
                print(f"  Found text: '{text}' with selector '{sel}'")
                
                # Extract number
                nums = re.findall(r'[\d,]+', text)
                if nums:
                    # Take the one that looks like a result count (often the first if it's "1-24 of 1,234")
                    val = int(nums[-1].replace(',', ''))
                    if val > count: count = val
            except:
                continue
        
        return count
    except Exception as e:
        print(f"  Error checking {url}: {e}")
        return 0

async def main():
    # Store: Yakima #3240 (confirmed by subagent)
    store_id = "3240"
    
    # Hierarchy to test:
    # Parent: Power Tools (4294612503)
    # Child 1: Drills (4294857470)
    # Child 2: Saws (4294857471)
    
    urls = [
        ("Power Tools (Parent)", "https://www.lowes.com/pl/Power-tools-Tools/4294612503"),
        ("Drills (Child)", "https://www.lowes.com/pl/Drills-Power-tools-Tools/4294857470"),
        ("Saws (Child)", "https://www.lowes.com/pl/Saws-Power-tools-Tools/4294857471")
    ]
    
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        # Use Chromium, headed, as per working Cheapskater config
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Testing store {store_id} hierarchy...")
        
        results = []
        for name, url in urls:
            count = await get_count(page, url, store_id)
            results.append((name, count))
            
        print("\nSUMMARY:")
        for name, count in results:
            print(f"  {name}: {count} items")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
