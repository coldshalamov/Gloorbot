import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

async def test_lowes_access():
    print("Starting v0.4.0 Diagnostic Test...")
    
    async with async_playwright() as p:
        # 1. Setup profile dir (matching worker)
        profile_dir = Path("test_profile_v4")
        profile_dir.mkdir(exist_ok=True)
        
        # 2. Match the NEW launch_kwargs exactly
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

        # 3. Apply Stealth (the key fix from Cheapskater)
        if HAS_STEALTH:
            print("Applying Stealth hook...")
            stealth = Stealth(
                navigator_languages_override=("en-US", "en"),
                navigator_platform_override="Win32",
                navigator_vendor_override="Google Inc.",
            )
            stealth.hook_playwright_context(p)
        else:
            print("WARNING: playwright-stealth not found. Run: pip install playwright-stealth")

        print("Launching Chromium (Cheapskater approach)...")
        context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            print("Navigating to Lowe's...")
            # We'll go to the homepage first like a normal human
            await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=60000)
            
            # Wait for a bit (human-like)
            print("Waiting for page loads...")
            await asyncio.sleep(5)
            
            # Take a screenshot to verify
            screenshot_path = "lowes_test_v4.png"
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")
            
            title = await page.title()
            print(f"Page Title: {title}")
            
            if "pardon" in title.lower() or "access denied" in title.lower():
                print("\n❌ STILL BLOCKED: Anti-bot detected us.")
            else:
                print("\n✅ SUCCESS: Reached homepage without block screen!")
                
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    # Ensure dependencies are installed
    os.system("pip install playwright-stealth")
    asyncio.run(test_lowes_access())
