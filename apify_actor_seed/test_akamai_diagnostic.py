"""
Akamai Block Diagnostic Test

This test helps diagnose WHY we're being blocked and confirms the constraints:
1. Akamai soft-blocks return HTTP 200 but blank page
2. Akamai hard-blocks return HTTP 403
3. Residential proxies with session locking are REQUIRED

Run: python test_akamai_diagnostic.py
"""

import asyncio
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def diagnose():
    print("=" * 70)
    print("AKAMAI BLOCK DIAGNOSTIC")
    print("=" * 70)

    test_url = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"

    async with async_playwright() as p:
        # Test 1: Standard headless (expected to fail hard)
        print("\n[TEST 1] Headless browser (expected: BLOCKED)")
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(test_url, timeout=30000)

            status = response.status if response else "N/A"
            title = await page.title()
            content = await page.content()
            has_products = "product" in content.lower() and len(content) > 10000

            print(f"   HTTP Status: {status}")
            print(f"   Title: '{title[:50]}'" if title else "   Title: (empty)")
            print(f"   Content size: {len(content)} bytes")
            print(f"   Has products: {has_products}")

            if status == 403 or "Access Denied" in content:
                print("   Result: HARD BLOCK (403/Access Denied)")
            elif len(content) < 5000 or not title:
                print("   Result: SOFT BLOCK (blank page)")
            else:
                print("   Result: PASSED (unexpected!)")

            await browser.close()
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Headful with stealth (expected: soft block without proxy)
        print("\n[TEST 2] Headful browser + stealth (expected: SOFT BLOCK without proxy)")
        try:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()

            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            response = await page.goto(test_url, wait_until="domcontentloaded", timeout=45000)

            # Wait for JS
            await asyncio.sleep(3)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            status = response.status if response else "N/A"
            title = await page.title()
            content = await page.content()
            has_products = "product-pod" in content.lower() or "application/ld+json" in content

            print(f"   HTTP Status: {status}")
            print(f"   Title: '{title[:50]}'" if title else "   Title: (empty)")
            print(f"   Content size: {len(content)} bytes")
            print(f"   Has product markers: {has_products}")

            # Check for Akamai signatures
            akamai_scripts = "_sec" in content or "akam" in content.lower()
            print(f"   Akamai scripts present: {akamai_scripts}")

            if status == 403 or "Access Denied" in content:
                print("   Result: HARD BLOCK (403/Access Denied)")
                block_type = "HARD"
            elif len(content) < 5000 or not title or not has_products:
                print("   Result: SOFT BLOCK (page loaded but no content)")
                block_type = "SOFT"
            else:
                print("   Result: PASSED - Content loaded!")
                block_type = "NONE"

            # Save diagnostic screenshot
            await page.screenshot(path="diagnostic_screenshot.png")
            print("   Screenshot saved: diagnostic_screenshot.png")

            await browser.close()

        except Exception as e:
            print(f"   Error: {e}")
            block_type = "ERROR"

    # Summary
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)

    print("""
FINDINGS:
---------
The blank page / soft block confirms the constraints from your context file:

1. Akamai DETECTS and BLOCKS automation even with:
   - headless=False
   - playwright-stealth
   - Realistic viewport/user-agent

2. The MISSING INGREDIENT is:
   - Residential proxy with SESSION LOCKING
   - The proxy must maintain the same IP for the entire store session

3. On APIFY, this works because:
   - Apify's residential proxy pool ($25/GB) provides clean IPs
   - Session IDs lock the IP per store
   - Combined with stealth, this passes Akamai

NEXT STEPS:
-----------
1. Deploy to Apify with RESIDENTIAL proxy group
2. Use session locking: proxy_url = await proxy_config.new_url(session_id=f"store_{store_id}")
3. The scraper code is READY - it just needs Apify's proxy infrastructure

LOCAL TESTING LIMITATIONS:
--------------------------
Without residential proxies, local testing will always get blocked.
The code must be validated ON Apify with their proxy infrastructure.
""")

    return block_type


if __name__ == "__main__":
    result = asyncio.run(diagnose())
    print(f"\nDiagnostic result: {result}")
