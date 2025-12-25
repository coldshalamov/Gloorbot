#!/usr/bin/env python3
"""
Akamai Bypass Test Script

This script tests whether the anti-fingerprinting measures work against
Lowe's Akamai bot detection. It will:
1. Launch Chrome (not Chromium) in visible mode
2. Apply all fingerprint randomization
3. Navigate to Lowe's and check if we're blocked

SUCCESS: Page loads with products visible
FAILURE: "Access Denied" or Akamai block page appears

Run with: python test_akamai_bypass.py
"""

import asyncio
import os
import random
import sys
from pathlib import Path

# Add the apify_actor_seed to the path
sys.path.insert(0, str(Path(__file__).parent / "apify_actor_seed" / "src"))

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Import fingerprint functions from main.py
try:
    from main import (
        build_fingerprint_profile,
        apply_fingerprint_randomization,
        USER_AGENTS,
        browser_channel,
    )
    IMPORTS_OK = True
except ImportError as e:
    print(f"Warning: Could not import from main.py: {e}")
    IMPORTS_OK = False


async def test_akamai_bypass():
    """Test if we can access Lowe's without getting blocked."""

    print("=" * 60)
    print("AKAMAI BYPASS TEST")
    print("=" * 60)

    # Test URL - a category page that exists
    test_url = "https://www.lowes.com/pl/On-sale--Paint/4294644082?refinement=4294417656"

    print(f"\nTarget URL: {test_url}")
    print(f"Browser channel: {browser_channel() if IMPORTS_OK else 'chrome (default)'}")
    print("\nLaunching browser...")

    async with async_playwright() as p:
        # Use real Chrome, not Chromium!
        channel = browser_channel() if IMPORTS_OK else "chrome"

        browser = await p.chromium.launch(
            headless=False,  # CRITICAL: Akamai blocks headless
            channel=channel,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1440,900",
                "--start-maximized",
            ],
        )

        # Create context with realistic settings
        viewport_width = 1440
        viewport_height = 900
        user_agent = random.choice(USER_AGENTS) if IMPORTS_OK else (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/Los_Angeles",
            color_scheme="light",
        )

        page = await context.new_page()

        # Apply stealth
        print("Applying playwright-stealth...")
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Apply fingerprint randomization
        if IMPORTS_OK:
            print("Applying fingerprint randomization...")
            fingerprint_profile = build_fingerprint_profile(viewport_width, viewport_height)
            await apply_fingerprint_randomization(page, fingerprint_profile)
        else:
            print("Warning: Could not apply fingerprint randomization (import failed)")

        # Navigate to Lowe's
        print(f"\nNavigating to {test_url}...")
        try:
            response = await page.goto(test_url, timeout=60000, wait_until="domcontentloaded")

            # Check for blocks
            title = await page.title()
            url = page.url

            print(f"\nResponse status: {response.status if response else 'N/A'}")
            print(f"Page title: {title}")
            print(f"Final URL: {url}")

            # Check for Akamai block indicators
            blocked = False
            block_reasons = []

            if response and response.status == 403:
                blocked = True
                block_reasons.append("HTTP 403 Forbidden")

            if "access denied" in title.lower():
                blocked = True
                block_reasons.append("'Access Denied' in page title")

            if "edgesuite" in url.lower() or "akamai" in url.lower():
                blocked = True
                block_reasons.append("Redirected to Akamai block page")

            # Check for product content
            try:
                products = await page.locator('[data-testid="product-card"], .product-card, .plp-pod').count()
                print(f"Products found: {products}")
            except Exception:
                products = 0

            print("\n" + "=" * 60)
            if blocked:
                print("RESULT: BLOCKED BY AKAMAI")
                print(f"Reasons: {', '.join(block_reasons)}")
                print("\nPossible solutions:")
                print("1. Wait 24-48 hours for IP to cool down")
                print("2. Try a different network (mobile hotspot)")
                print("3. Check if Chrome is installed (not just Chromium)")
            elif products > 0:
                print("RESULT: SUCCESS! Page loaded with products.")
                print(f"Found {products} product cards on the page.")
            else:
                print("RESULT: PARTIAL SUCCESS")
                print("Page loaded but no products found.")
                print("This might be a page layout issue, not a block.")
            print("=" * 60)

            # Keep browser open for manual inspection
            print("\nBrowser will stay open for 30 seconds for inspection...")
            print("Press Ctrl+C to close early.")
            try:
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                pass

        except Exception as e:
            print(f"\nError during navigation: {e}")
            print("\nThis might indicate:")
            print("1. Network issues")
            print("2. Chrome not installed")
            print("3. Akamai blocking at connection level")

        finally:
            await browser.close()


if __name__ == "__main__":
    print("\nStarting Akamai bypass test...")
    print("Make sure Chrome is installed on your system!")
    print("")

    asyncio.run(test_akamai_bypass())
