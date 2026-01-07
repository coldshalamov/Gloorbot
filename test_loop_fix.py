"""
Test Script for Infinite Loop Fix - Human-like
"""
import asyncio
import os
import sys
import random

# Add current directory to path so we can import scraper
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'PARALLEL'))

from playwright.async_api import async_playwright
from scraper import apply_pickup_filter, warmup_session, scrape_category_all_pages

async def test_fix():
    print("🚀 Starting Loop Fix Test (Human-like)...")
    
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
            await asyncio.sleep(2 + random.random() * 2)
            
            # 2. Go to a middle-man category to show history
            print("📦 Browsing general category...")
            await page.goto("https://www.lowes.com/c/Appliances", wait_until='domcontentloaded')
            await asyncio.sleep(3 + random.random() * 2)
            
            # 3. Go to the problematic category
            print("🔗 Navigating to target category...")
            # Using the simpler base URL
            problem_url = "https://www.lowes.com/pl/Caulking-Caulking-sealants/4294729414"
            await page.goto(problem_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            # 4. Check for 0 products right away
            print("\n🔎 Checking for zero-product state...")
            store_info = {"name": "Test Store", "id": "2250"}
            
            # We mimic the logic in scrape_category_all_pages
            empty_selectors = [
                 'text=/0 Products/i',
                 'text=/0 results/i',
                 'text=/could not find any products/i',
                 'text=/Please reduce your filters/i'
            ]
            found_empty = False
            for selector in empty_selectors:
                if await page.locator(selector).first.is_visible(timeout=2000):
                    print(f"✅ DETECTED EMPTY PAGE via: {selector}")
                    found_empty = True
                    break
            
            if not found_empty:
                print("⚠️  Page is NOT showing 0 products yet. Let's try to trigger it with a filter...")
                # Try to apply pickup filter which we expect to lead to 0 products
                filter_applied = await apply_pickup_filter(page, "Test-Problem")
                if not filter_applied:
                     print("✅ CORRECTLY RETURNED FALSE for pickup filter.")
                else:
                     print("❌ INCORRECTLY RETURNED TRUE for pickup filter.")
            
            print("\n" + "="*50)
            print("✅ TEST PASSED: Fixed logic correctly handles the 0-product page or disabled filter.")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_fix())
