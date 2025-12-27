import asyncio
import json
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STORE_ID = "3240"

async def get_sidebar_categories(page, url):
    print(f"Scraping sidebar from: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        # Look for "Category" filter in the sidebar
        # Often has a "View More" button
        try:
            more_btn = await page.wait_for_selector("button:has-text('View More')", timeout=5000)
            if more_btn: await more_btn.click()
        except: pass
        
        # Extract all category links and their associated counts from the sidebar
        # Pattern: a link containing /pl/ and a sibling/child span with a count (e.g. "(123)")
        links = await page.eval_on_selector_all("section:has-text('Category') a[href*='/pl/']", """
            elements => elements.map(e => {
                const countText = e.parentElement.innerText.match(/\((\d+)\)/);
                return {
                    href: e.href,
                    text: e.innerText,
                    count: countText ? parseInt(countText[1]) : 0
                };
            })
        """)
        
        return links
    except Exception as e:
        print(f"  Error: {e}")
        return []

async def main():
    async with async_playwright() as p:
        stealth = Stealth()
        stealth.hook_playwright_context(p)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Start at a very broad search
        start_url = f"https://www.lowes.com/search?searchTerm=a&storeId={STORE_ID}&inStock=1"
        
        all_categories = {} # id -> {url, count}
        
        # Layer 1
        l1 = await get_sidebar_categories(page, start_url)
        for item in l1:
            match = re.search(r'/(\d+)$', item['href'].split('?')[0])
            if match:
                cid = match.group(1)
                all_categories[cid] = {"url": item['href'].split('?')[0], "count": item['count'], "name": item['text']}
        
        print(f"Found {len(all_categories)} top-level categories from sidebar.")
        
        with open("sidebar_discovery_layer1.json", "w") as f:
            json.dump(all_categories, f, indent=2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
