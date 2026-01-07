"""
MOCK TEST for 0 Products Detection
Injects the '0 Products' text into a page to verify the detection logic works.
"""
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'PARALLEL'))

from playwright.async_api import async_playwright
from scraper import scrape_category_all_pages

async def test_mock_empty():
    print("🚀 Starting MOCK Empty Results Test...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Load a simple page (can even be blank)
        await page.goto("about:blank")
        
        # 2. Inject the "0 Products" text that we saw in the screenshot
        print("💉 Injecting '0 Products' text into page...")
        await page.evaluate("""
            () => {
                const div = document.createElement('div');
                div.innerHTML = '<h1>0 Products.</h1><p>Please reduce your filters.</p>';
                document.body.appendChild(div);
            }
        """)
        
        # 3. Call scrape_category_all_pages
        # We expect it to detect the text and return [] IMMEDIATELY
        print("🔎 Calling scrape_category_all_pages...")
        store_info = {"name": "Test Store", "id": "2250"}
        
        # Note: We need to bypass the initial load check, but scrape_category_all_pages
        # starts by loading the URL. We'll use a local file to avoid network.
        with open("empty_test.html", "w") as f:
            f.write("<html><body><h1>0 Products.</h1></body></html>")
        
        url = "file://" + os.path.abspath("empty_test.html")
        
        products = await scrape_category_all_pages(page, url, store_info)
        
        print("\n" + "="*50)
        if products == []:
            print("✅ TEST PASSED: Scraper correctly detected '0 Products' and returned an empty list.")
        else:
            print(f"❌ TEST FAILED: Scraper returned {len(products)} products or didn't abort!")
        print("="*50 + "\n")
        
        await browser.close()
        if os.path.exists("empty_test.html"):
            os.remove("empty_test.html")

if __name__ == "__main__":
    asyncio.run(test_mock_empty())
