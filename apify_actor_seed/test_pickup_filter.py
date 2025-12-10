"""
Focused Test: Pickup Filter Race Condition Fix

This test specifically verifies that the pickup filter works correctly.
Run this FIRST to validate the fix before running full scraper tests.

Usage:
    python test_pickup_filter.py
"""

import asyncio
import random
import re
from typing import Any

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


# Test URLs - categories known to have "Pickup Today" filter
TEST_URLS = [
    # Lumber - high volume, always has pickup items
    "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532",
    # Power tools - good test for filter visibility
    "https://www.lowes.com/pl/Power-tools-Tools/4294612503",
    # The Back Aisle - clearance items
    "https://www.lowes.com/pl/The-back-aisle/2021454685607",
]


async def test_pickup_filter(page: Any, url: str) -> dict:
    """Test the pickup filter on a single URL and return results."""

    result = {
        "url": url,
        "page_loaded": False,
        "filter_found": False,
        "filter_clicked": False,
        "filter_verified": False,
        "products_before": 0,
        "products_after": 0,
        "error": None,
    }

    try:
        # Navigate to page
        print(f"\n{'='*60}")
        print(f"Testing: {url[:60]}...")

        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        if response and response.status >= 400:
            result["error"] = f"HTTP {response.status}"
            return result

        result["page_loaded"] = True

        # Wait for network idle
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            print("  Warning: Network idle timeout")

        await asyncio.sleep(1)

        # Count products BEFORE filter
        async def count_products():
            try:
                cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
                return len(cards)
            except Exception:
                return -1

        result["products_before"] = await count_products()
        print(f"  Products before filter: {result['products_before']}")

        # Pickup filter selectors
        pickup_selectors = [
            'label:has-text("Get It Today")',
            'label:has-text("Pickup Today")',
            'label:has-text("Available Today")',
            'button:has-text("Pickup")',
            'button:has-text("Get It Today")',
            'button:has-text("Get it fast")',
            '[data-testid*="pickup"]',
            '[aria-label*="Pickup"]',
            '[aria-label*="Get it today"]',
            'input[type="checkbox"][id*="pickup"]',
        ]

        # Try to expand availability section first
        availability_toggles = [
            'button:has-text("Availability")',
            'button:has-text("Get It Fast")',
            'summary:has-text("Availability")',
        ]

        for toggle_sel in availability_toggles:
            try:
                toggle = await page.query_selector(toggle_sel)
                if toggle:
                    expanded = await toggle.get_attribute("aria-expanded")
                    if expanded == "false":
                        print(f"  Expanding availability section...")
                        await toggle.click()
                        await asyncio.sleep(0.5)
                    break
            except Exception:
                continue

        # Find and click pickup filter
        filter_element = None
        filter_text = ""

        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    visible = await el.is_visible()
                    if visible:
                        try:
                            filter_text = (await el.inner_text()) or ""
                        except Exception:
                            filter_text = ""

                        if len(filter_text) < 100:  # Sanity check
                            filter_element = el
                            result["filter_found"] = True
                            print(f"  Filter found: '{filter_text[:50]}' via {selector}")
                            break

                if filter_element:
                    break
            except Exception:
                continue

        if not filter_element:
            result["error"] = "Pickup filter not found"
            print("  ERROR: Pickup filter NOT FOUND!")
            return result

        # Check if already selected
        async def is_selected(el):
            try:
                for attr in ["aria-checked", "aria-pressed", "aria-selected"]:
                    val = await el.get_attribute(attr)
                    if val == "true":
                        return True
                try:
                    return await el.is_checked()
                except Exception:
                    return False
            except Exception:
                return False

        already_selected = await is_selected(filter_element)
        if already_selected:
            print("  Filter already selected!")
            result["filter_clicked"] = True
            result["filter_verified"] = True
            result["products_after"] = result["products_before"]
            return result

        # Get URL before click
        url_before = page.url

        # Click the filter
        print(f"  Clicking filter...")
        await filter_element.click()
        result["filter_clicked"] = True

        await asyncio.sleep(1)

        # Wait for page to update
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass

        await asyncio.sleep(1)

        # VERIFY filter was applied
        url_after = page.url

        # Check 1: URL changed
        if url_after != url_before:
            if "pickup" in url_after.lower() or "availability" in url_after.lower():
                print(f"  Verified via URL change")
                result["filter_verified"] = True

        # Check 2: Element is now selected
        if not result["filter_verified"]:
            if await is_selected(filter_element):
                print(f"  Verified via aria-checked/pressed")
                result["filter_verified"] = True

        # Check 3: Product count changed
        result["products_after"] = await count_products()
        if not result["filter_verified"]:
            if result["products_after"] != result["products_before"] and result["products_after"] != -1:
                print(f"  Verified via product count change: {result['products_before']} -> {result['products_after']}")
                result["filter_verified"] = True

        if not result["filter_verified"]:
            print("  WARNING: Could not verify filter application!")

        print(f"  Products after filter: {result['products_after']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"  ERROR: {e}")

    return result


async def main():
    print("=" * 60)
    print("PICKUP FILTER RACE CONDITION TEST")
    print("=" * 60)
    print("\nThis test validates the pickup filter fix.")
    print("We'll test multiple category pages and verify the filter works.\n")

    async with async_playwright() as playwright:
        # Launch browser (headful for better debugging)
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

        results = []

        for url in TEST_URLS:
            result = await test_pickup_filter(page, url)
            results.append(result)
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for r in results:
        status = "PASS" if r["filter_verified"] else "FAIL"
        if r["filter_verified"]:
            passed += 1
        else:
            failed += 1

        print(f"\n[{status}] {r['url'][:50]}...")
        print(f"       Page loaded: {r['page_loaded']}")
        print(f"       Filter found: {r['filter_found']}")
        print(f"       Filter clicked: {r['filter_clicked']}")
        print(f"       Filter verified: {r['filter_verified']}")
        print(f"       Products: {r['products_before']} -> {r['products_after']}")
        if r["error"]:
            print(f"       Error: {r['error']}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 60)

    if failed > 0:
        print("\nSome tests failed! The pickup filter may need adjustment.")
        return 1
    else:
        print("\nAll tests passed! The pickup filter fix is working.")
        return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
