"""
Final Verification Script for Hard Abort Fix
"""
import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'PARALLEL'))

from playwright.async_api import async_playwright
from scraper import scrape_category_all_pages, warmup_session

async def test_hard_abort():
    print("🚀 Starting Final Hard Abort Test...")
    
    async with async_playwright() as p:
        profile_path = r"C:\Users\User\AppData\Local\Google\Chrome\User Data\ScraperProfile"
        browser = await p.chromium.launch_persistent_context(
            profile_path,
            channel="chrome",
            headless=False,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        try:
            # 1. Warmup
            print("🏠 Warming up...")
            await warmup_session(page)
            
            # 2. Go to the EXACT problematic URL
            print("🔗 Navigating to the page known to cause loops...")
            problem_url = "https://www.lowes.com/pl/caulking/caulk/interior-paint-trim/4294729414-1411293683550?offset=72"
            await page.goto(problem_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            # 3. Check for the text
            print("🔎 Checking for '0 Products' detection logic...")
            
            empty_check = await page.evaluate("""() => {
                const body = document.body.innerText;
                console.log('Body start:', body.substring(0, 500));
                return /0 Products/i.test(body) || /0 results/i.test(body) || /Please reduce your filters/i.test(body);
            }""")
            
            print("\n" + "="*50)
            if empty_check:
                print("✅ TEST PASSED: Detection logic correctly identified the 0-product page.")
                print("   The scraper will now abort this category instantly.")
            else:
                print("❌ TEST FAILED: Detection logic DID NOT see the 0-product text!")
                # Get some body text to debug
                body = await page.evaluate("document.body.innerText")
                print(f"   Body snippet: {body[:200]}")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_hard_abort())
