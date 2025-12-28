"""
Test v0.7.0 - No stealth library, just browser args
"""
import asyncio
from pathlib import Path
import shutil

async def main():
    print("="*60)
    print("v0.7.0 TEST - No stealth, just browser args")
    print("="*60)
    
    # Clean profile
    profile = Path("test_v7_profile")
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir()
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # Exact config from v0.7.0 slot_worker.py - NO STEALTH
        launch_kwargs = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",  # This hides webdriver
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
        
        print("Launching browser (NO stealth library)...")
        context = await p.chromium.launch_persistent_context(str(profile), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Check webdriver
        wd = await page.evaluate("navigator.webdriver")
        print(f"navigator.webdriver = {wd}")
        
        print("Navigating to Lowe's...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        
        await asyncio.sleep(5)
        
        title = await page.title()
        print(f"Page title: {title}")
        
        if "pardon" in title.lower() or "denied" in title.lower():
            print(">>> BLOCKED <<<")
        else:
            print(">>> SUCCESS <<<")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
