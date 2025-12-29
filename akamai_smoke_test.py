import asyncio
from playwright.async_api import async_playwright
import os

# Test target - a real product listing page protected by Akamai
TARGET_URL = "https://www.lowes.com/pl/Extension-cords-surge-protectors-Electrical/4294934373"

async def smoke_test():
    print(f"Running Akamai Smoke Test against: {TARGET_URL}")
    print("Configuration: Playwright 1.56.0 (System Default)")
    
    async with async_playwright() as p:
        # Match the worker's new configuration (No spoofing, simple launch)
        launch_kwargs = {
            "headless": False, 
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process", 
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
            ]
        }
        
        # Optional channel check
        if os.getenv("GLOORBOT_BROWSER_CHANNEL"):
             print(f"Using custom channel: {os.getenv('GLOORBOT_BROWSER_CHANNEL')}")
             launch_kwargs["channel"] = os.getenv("GLOORBOT_BROWSER_CHANNEL")

        print("Launching browser...")
        browser = await p.chromium.launch(**launch_kwargs)
        
        print("Creating context...")
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
        
        page = await context.new_page()
        
        print("Navigating to product page...")
        try:
            await page.goto(TARGET_URL, timeout=30000)
            await asyncio.sleep(5)
            
            title = await page.title()
            url = page.url
            
            is_blocked = "access denied" in title.lower() or "edgesuite" in url.lower()
            
            print("-" * 50)
            print(f"Page Title: {title}")
            print(f"Final URL:  {url}")
            print("-" * 50)
            
            if is_blocked:
                print("❌ RESULT: BLOCKED (Access Denied)")
            else:
                print("✅ RESULT: SUCCESS (Content Loaded)")
                # Evaluate product count
                count = await page.evaluate("document.querySelectorAll('.product-card').length")
                print(f"Products found on page: {count}")
                
        except Exception as e:
            print(f"❌ Error during navigation: {e}")
            
        await browser.close()
        print("Test complete.")

if __name__ == "__main__":
    asyncio.run(smoke_test())
