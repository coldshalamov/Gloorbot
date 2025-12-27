"""
Simplest possible test - just load Lowes homepage
"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Loading https://www.lowes.com/...")
        try:
            await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
            print(f"Title: {await page.title()}")
            print(f"URL: {page.url}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            await page.screenshot(path="test_homepage.png")
            await browser.close()

asyncio.run(test())
