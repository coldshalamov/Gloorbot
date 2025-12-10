"""
Test with Lowe's store locator (less protected than category pages)

The Lowe's store locator page has fewer anti-bot protections, making it
a good test for the scraper logic without needing real proxies.
"""

import asyncio
import json
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def main():
    print("=" * 60)
    print("LOWE'S STORE LOCATOR TEST")
    print("=" * 60)
    print("\nTesting with less-protected pages (store locator)")
    print()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
        )

        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        try:
            # Try store locator (less protected)
            print("Navigating to Lowe's homepage...")
            response = await page.goto("https://www.lowes.com", wait_until="domcontentloaded", timeout=60000)

            print(f"Response status: {response.status if response else 'N/A'}")

            content = await page.content()

            # Check for blocks
            if "Access Denied" in content:
                print("[X] BLOCKED by Akamai on homepage too")
            else:
                print("[+] Homepage loaded successfully")
                title = await page.title()
                print(f"    Title: {title}")

                # Try to extract some store info from the page
                stores_text = content[:2000]  # First 2000 chars
                if "store" in stores_text.lower():
                    print("[+] Found store references in page")

            # Take screenshot
            await page.screenshot(path="test_homepage.png", full_page=False)
            print("Screenshot saved")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            await browser.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
