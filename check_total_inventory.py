import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def get_total_inventory(store_id="0707", search_term="*"):
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Set Store Context
        store_url = f"https://www.lowes.com/store/wa/yakima/{store_id}" # Example Yakima store
        print(f"Loading store page: {store_url}")
        await page.goto(store_url, wait_until="domcontentloaded")
        
        # Try to set as my store
        try:
            btn = await page.wait_for_selector("button:has-text('Set as My Store')", timeout=5000)
            if btn: await btn.click()
        except: pass
        
        await asyncio.sleep(2)
        
        # Search for wildcard
        search_url = f"https://www.lowes.com/search?searchTerm={search_term}&inStock=1&rollUpVariants=0"
        print(f"Searching: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Look for "Pickup Today" or "Get it Today" filter to get local inventory count
        try:
            # Applying filter usually updates the results count
            filter_btn = await page.wait_for_selector("label:has-text('Pickup Today'), label:has-text('Get It Today')", timeout=5000)
            if filter_btn: 
                print("Clicking Pickup Today filter...")
                await filter_btn.click()
                await asyncio.sleep(3)
        except:
             print("Could not find Pickup Today filter")

        # Get the result count text
        try:
            count_elem = await page.wait_for_selector("[class*='resultCount'], [class*='results-count'], h1:has-text('Results')", timeout=5000)
            count_text = await count_elem.inner_text()
            print(f"Count text found: {count_text}")
        except:
            print("Could not find result count element")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_total_inventory())
