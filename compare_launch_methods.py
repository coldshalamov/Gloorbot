"""
Compare browser launch methods between Cheapskater and GloorbotWorker
"""
import asyncio
from pathlib import Path
import shutil
from playwright.async_api import async_playwright

async def test_persistent_vs_normal():
    print("\n" + "="*70)
    print("TESTING: launch_persistent_context() vs launch() + new_context()")
    print("="*70 + "\n")
    
    # Clean profiles
    profile_persistent = Path("test_profile_persistent")
    if profile_persistent.exists():
        shutil.rmtree(profile_persistent)
    
    async with async_playwright() as p:
        launch_args = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
            ],
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
        }
        
        # TEST 1: GloorbotWorker approach (launch_persistent_context)
        print("TEST 1: launch_persistent_context() - GloorbotWorker style")
        print("-"*70)
        profile_persistent.mkdir()
        context_persistent = await p.chromium.launch_persistent_context(
            str(profile_persistent),
            **launch_args
        )
        page1 = context_persistent.pages[0] if context_persistent.pages else await context_persistent.new_page()
        
        await page1.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Check for automation markers
        webdriver = await page1.evaluate("navigator.webdriver")
        title1 = await page1.title()
        
        # Take screenshot
        await page1.screenshot(path="test_persistent.png")
        
        print(f"navigator.webdriver: {webdriver}")
        print(f"Title: {title1}")
        print(f"Screenshot: test_persistent.png")
        
        await context_persistent.close()
        
        print("\nWaiting 5 seconds before next test...")
        await asyncio.sleep(5)
        
        # TEST 2: Cheapskater approach (launch + new_context)  
        print("\nTEST 2: chromium.launch() + new_context() - Cheapskater style")
        print("-"*70)
        
        browser = await p.chromium.launch(**{
            "headless": False,
            "args": launch_args["args"],
        })
        
        context_normal = await browser.new_context(
            viewport=launch_args["viewport"],
            locale=launch_args["locale"],
        )
        
        page2 = await context_normal.new_page()
        
        await page2.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Check for automation markers
        webdriver2 = await page2.evaluate("navigator.webdriver")
        title2 = await page2.title()
        
        # Take screenshot
        await page2.screenshot(path="test_normal_context.png")
        
        print(f"navigator.webdriver: {webdriver2}")
        print(f"Title: {title2}")
        print(f"Screenshot: test_normal_context.png")
        
        await browser.close()
        
    print("\n" + "="*70)
    print("TEST COMPLETE - Check screenshots for visual differences")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_persistent_vs_normal())
