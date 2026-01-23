"""Test against ACTUAL product listing pages"""
import asyncio
import random
from playwright.async_api import async_playwright

DEFAULT_UAS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.23 Safari/537.36",
)

PRODUCT_PAGE = "https://www.lowes.com/pl/Extension-cords-surge-protectors-Electrical/4294934373"

async def test():
    print("Testing product page with full hardening...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, user_agent=DEFAULT_UAS[0])
        
        # Headers
        await context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-CH-UA": '"Not A(Brand)";v="99", "Chromium";v="125"',
            "Sec-CH-UA-Mobile": "?0",
        })
        
        # Init script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
        """)
        
        page = await context.new_page()
        await page.goto(PRODUCT_PAGE, timeout=30000)
        await asyncio.sleep(3)
        
        title = await page.title()
        is_blocked = "access denied" in title.lower()
        
        print(f"Title: {title}")
        print(f"Result: {'BLOCKED' if is_blocked else 'SUCCESS'}")
        
        await page.screenshot(path="test_result.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
