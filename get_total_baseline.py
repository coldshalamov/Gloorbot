import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re

async def get_total_yakima_count():
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Go to a search results page for '*' with Yakima store
        # 0707 was Martinsville, 3240 is Yakima.
        url = "https://www.lowes.com/search?searchTerm=*&storeId=3240&inStock=1&rollUpVariants=0"
        print(f"Checking total inventory at: {url}")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10) # Wait for count to settle
        
        selectors = [
            "[data-testid='total-results']",
            ".total-results",
            "span[class*='total-results']",
            "div[class*='resultCount']"
        ]
        
        total_count = 0
        for sel in selectors:
            try:
                elem = await page.wait_for_selector(sel, timeout=10000)
                text = await elem.inner_text()
                print(f"  Found count text: '{text}' with {sel}")
                nums = re.findall(r'[\d,]+', text)
                if nums:
                    total_count = int(nums[-1].replace(',', ''))
                    break
            except: continue
            
        print(f"\nTOTAL CALCULATED INVENTORY FOR STORE 3240: {total_count}")
        await browser.close()
        return total_count

if __name__ == "__main__":
    asyncio.run(get_total_yakima_count())
