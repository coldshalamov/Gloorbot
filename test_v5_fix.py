"""
Test v0.5.0 fix: stealth_async(page) applied per-page BEFORE navigation
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_v5_stealth_fix():
    print("Testing v0.5.0 stealth fix...")
    print("Pattern: stealth_async(page) called AFTER page creation, BEFORE navigation")
    print()
    
    profile_dir = Path("test_profile_v5")
    profile_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Exact same launch_kwargs as slot_worker.py
        launch_kwargs = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
                "--start-maximized",
                "--window-size=1440,960",
            ],
            "slow_mo": 12,
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
        }
        
        print("1. Launching browser with persistent context...")
        context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        
        # THE FIX: Apply stealth AFTER page creation, BEFORE navigation
        print("2. Applying stealth_async(page) - the corrected pattern...")
        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
            print("   SUCCESS: Stealth applied to page")
        except Exception as e:
            print(f"   WARNING: Stealth failed: {e}")
        
        # Check navigator.webdriver BEFORE navigation
        print("3. Checking navigator.webdriver before navigation...")
        webdriver_value = await page.evaluate("navigator.webdriver")
        print(f"   navigator.webdriver = {webdriver_value}")
        if webdriver_value is True:
            print("   WARNING: webdriver is TRUE - stealth may not be working!")
        else:
            print("   GOOD: webdriver is hidden/undefined")
        
        # Now navigate
        print("4. Navigating to Lowe's homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)
        
        # Check results
        title = await page.title()
        print(f"5. Page title: {title}")
        
        # Screenshot
        await page.screenshot(path="test_v5_result.png")
        print("6. Screenshot saved to test_v5_result.png")
        
        if "pardon" in title.lower() or "access denied" in title.lower() or "robot" in title.lower():
            print()
            print("RESULT: BLOCKED - Akamai still detecting us")
        else:
            print()
            print("RESULT: SUCCESS - Page loaded without block!")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_v5_stealth_fix())
