"""
SIMPLE VISUAL TEST - Opens a browser window you can SEE
Run: python simple_visual_test.py
"""
import asyncio
from pathlib import Path
import shutil

async def main():
    print("="*60)
    print("SIMPLE VISUAL TEST")
    print("This will open a VISIBLE browser window")
    print("="*60)
    
    # Clean profile
    profile = Path("visual_test_profile")
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir()
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # Apply stealth (v2.0.0 API)
        try:
            from playwright_stealth import Stealth
            stealth = Stealth(
                navigator_languages_override=("en-US", "en"),
                navigator_platform_override="Win32",
                navigator_vendor_override="Google Inc.",
            )
            stealth.hook_playwright_context(p)
            print("Stealth enabled")
        except Exception as e:
            print(f"Stealth failed: {e}")
        
        print("Launching browser (headless=False, should be VISIBLE)...")
        
        context = await p.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage", 
                "--disable-infobars",
                "--start-maximized",
                "--window-size=1440,960",
            ],
            slow_mo=50,  # Slow down so you can see it
            viewport={"width": 1440, "height": 900},
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Check webdriver
        wd = await page.evaluate("navigator.webdriver")
        print(f"navigator.webdriver = {wd}")
        
        print("Navigating to Lowe's...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        
        print("Waiting 10 seconds so you can see the page...")
        await asyncio.sleep(10)
        
        title = await page.title()
        print(f"Page title: {title}")
        
        if "pardon" in title.lower() or "denied" in title.lower():
            print("\n>>> BLOCKED! <<<")
        else:
            print("\n>>> SUCCESS! Page loaded. <<<")
        
        print("\nClosing browser in 5 seconds...")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
