#!/usr/bin/env python3
"""
Test Anti-Fingerprinting Implementation
Tests the new fingerprinting measures against Lowe's Akamai protection
"""

import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import random

# Import our anti-fingerprinting functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from main import (
    apply_fingerprint_randomization,
    setup_request_interception,
    USER_AGENTS,
    TIMEZONES,
    LOCALES,
)


async def test_lowes_access():
    """Test accessing Lowe's with anti-fingerprinting enabled."""

    print("=" * 60)
    print("ANTI-FINGERPRINTING TEST - Lowe's.com")
    print("=" * 60)

    async with async_playwright() as pw:
        # Launch browser (headless=False like production)
        print("\n[1/5] Launching browser (headless=False)...")
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Create context with randomized fingerprint
        print("[2/5] Creating context with randomized fingerprint...")
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        selected_timezone = random.choice(TIMEZONES)
        selected_locale = random.choice(LOCALES)
        selected_ua = random.choice(USER_AGENTS)

        print(f"  Viewport: {viewport_width}x{viewport_height}")
        print(f"  Timezone: {selected_timezone}")
        print(f"  Locale: {selected_locale}")
        print(f"  User Agent: {selected_ua[:60]}...")

        context_opts = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "timezone_id": selected_timezone,
            "locale": selected_locale,
            "user_agent": selected_ua,
        }

        context = await browser.new_context(**context_opts)
        page = await context.new_page()

        # Apply anti-fingerprinting stack
        print("[3/5] Applying anti-fingerprinting stack...")
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        print("  ✓ Playwright-stealth applied")

        await apply_fingerprint_randomization(page)
        print("  ✓ Canvas noise injection")
        print("  ✓ WebGL randomization")
        print("  ✓ AudioContext noise")
        print("  ✓ Screen randomization")

        await setup_request_interception(page)
        print("  ✓ Resource blocking configured")

        # Navigate to Lowe's
        print("\n[4/5] Navigating to Lowe's Clearance page...")
        target_url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"

        try:
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

            print(f"  HTTP Status: {response.status}")

            # Check if blocked
            await asyncio.sleep(2)  # Let page settle
            title = await page.title()
            print(f"  Page Title: {title}")

            if "Access Denied" in title or response.status == 403:
                print("\n❌ BLOCKED - Akamai denied access")
                print("  This means the fingerprinting didn't work")
                success = False
            else:
                print("\n✅ SUCCESS - Page loaded!")
                print("  Akamai did NOT block the request")

                # Try to find products
                await asyncio.sleep(2)
                products = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
                print(f"  Products found: {len(products)}")
                success = True

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            success = False

        # Keep browser open for inspection
        print("\n[5/5] Test complete. Browser will stay open for 10 seconds...")
        print("  Check the page to verify it loaded correctly")
        await asyncio.sleep(10)

        await browser.close()

        print("\n" + "=" * 60)
        if success:
            print("✅ ANTI-FINGERPRINTING TEST: PASSED")
            print("The actor should work on Apify with residential proxies")
        else:
            print("❌ ANTI-FINGERPRINTING TEST: FAILED")
            print("More work needed - Akamai still detecting bot")
        print("=" * 60)

        return success


if __name__ == "__main__":
    success = asyncio.run(test_lowes_access())
    sys.exit(0 if success else 1)
