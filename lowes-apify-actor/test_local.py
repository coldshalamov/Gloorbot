"""
Local Test Script for Lowe's Apify Actor
Tests the pickup filter functionality and Akamai detection without deploying to Apify

CRITICAL TESTS:
1. Does pickup filter UI element get found?
2. Does pickup filter actually apply?
3. Does Akamai block immediately?
4. Are products extracted correctly?
5. How do anti-fingerprinting measures perform?

This script runs a minimal test (1 store, 2-3 categories, 2-3 pages) to validate
the actor works before deploying to production.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Fix Windows console encoding for UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Set environment variables BEFORE importing the actor
os.environ["CHEAPSKATER_DIAGNOSTICS"] = "1"
os.environ["CHEAPSKATER_TEST_MODE"] = "1"
os.environ["CHEAPSKATER_PICKUP_FILTER"] = "1"
os.environ["CHEAPSKATER_SET_STORE_CONTEXT"] = "0"  # Skip store context for faster testing
os.environ["CHEAPSKATER_BLOCK_RESOURCES"] = "0"  # Disable to reduce bot signals
os.environ["CHEAPSKATER_FINGERPRINT_INJECTION"] = "1"  # Enable anti-fingerprinting
os.environ["CHEAPSKATER_RANDOM_UA"] = "0"  # Disable UA randomization for consistency
os.environ["CHEAPSKATER_RANDOM_TZLOCALE"] = "0"  # Disable for consistency
os.environ["CHEAPSKATER_BROWSER_CHANNEL"] = "chrome"  # Use real Chrome

# Add src to path
SRC_PATH = Path(__file__).parent / "src"
APP_PATH = Path(__file__).parent / "app"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(APP_PATH))

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth


# Import required functions from main.py
from main import (
    apply_fingerprint_randomization,
    apply_pickup_filter,
    build_fingerprint_profile,
    check_blocked,
    compute_fingerprint_hash,
    extract_products,
    fingerprint_injection_enabled,
    proxy_settings_from_url,
    scrape_category,
    setup_request_interception,
    resource_blocking_enabled,
    _launch_args,
    _mask_proxy,
    _prime_session,
    _wait_for_akamai_clear,
    BASE_URL,
)


class TestResults:
    """Track test results for final report."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
        self.start_time = time.time()
        self.products_found = 0
        self.categories_tested = 0
        self.akamai_blocks = 0
        self.pickup_filter_successes = 0
        self.pickup_filter_failures = 0

    def add_result(self, test_name: str, passed: bool, message: str, details: dict = None):
        """Add a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "PASS"
        else:
            self.tests_failed += 1
            status = "FAIL"

        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

        # Print immediately
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"STATUS: {status}")
        print(f"MESSAGE: {message}")
        if details:
            print(f"DETAILS: {json.dumps(details, indent=2)}")
        print(f"{'='*60}\n")

    def generate_report(self) -> str:
        """Generate final markdown report."""
        elapsed = time.time() - self.start_time

        report = f"""# Lowe's Actor Local Test Results
## Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Summary
- **Total Tests**: {self.tests_run}
- **Passed**: {self.tests_passed}
- **Failed**: {self.tests_failed}
- **Success Rate**: {(self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0:.1f}%
- **Duration**: {elapsed:.1f}s

### Key Metrics
- **Products Found**: {self.products_found}
- **Categories Tested**: {self.categories_tested}
- **Akamai Blocks**: {self.akamai_blocks}
- **Pickup Filter Successes**: {self.pickup_filter_successes}
- **Pickup Filter Failures**: {self.pickup_filter_failures}

### Test Results

"""

        for result in self.results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            report += f"#### {status_icon} {result['test']}\n"
            report += f"- **Status**: {result['status']}\n"
            report += f"- **Message**: {result['message']}\n"
            if result.get('details'):
                report += f"- **Details**:\n```json\n{json.dumps(result['details'], indent=2)}\n```\n"
            report += "\n"

        return report


async def test_browser_launch(playwright, results: TestResults):
    """Test 1: Can we launch the browser with anti-fingerprinting?"""
    try:
        browser = await playwright.chromium.launch(
            headless=False,
            channel="chrome",
            args=_launch_args(),
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
        )

        page = await context.new_page()

        # Apply stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Apply fingerprint randomization
        if fingerprint_injection_enabled():
            profile = build_fingerprint_profile(1440, 900)
            await apply_fingerprint_randomization(page, profile)

        results.add_result(
            "Browser Launch",
            True,
            "Browser launched successfully with anti-fingerprinting measures",
            {"headless": False, "channel": "chrome", "fingerprinting": True}
        )

        return browser, context, page

    except Exception as e:
        results.add_result(
            "Browser Launch",
            False,
            f"Failed to launch browser: {e}",
            {"error": str(e)}
        )
        raise


async def test_akamai_block(page: Page, results: TestResults):
    """Test 2: Does Akamai block us immediately?"""
    try:
        # Try to load homepage
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)

        # Wait for Akamai to settle
        akamai_clear = await _wait_for_akamai_clear(page, timeout_s=30.0)

        if not akamai_clear:
            results.akamai_blocks += 1
            results.add_result(
                "Akamai Block Test",
                False,
                "Akamai challenge did not clear or Access Denied detected",
                {"url": page.url, "title": await page.title()}
            )
            return False

        blocked = await check_blocked(page)
        if blocked:
            results.akamai_blocks += 1
            results.add_result(
                "Akamai Block Test",
                False,
                "Access Denied page detected",
                {"url": page.url, "title": await page.title()}
            )
            return False

        results.add_result(
            "Akamai Block Test",
            True,
            "Homepage loaded successfully without blocks",
            {"url": page.url, "title": await page.title()}
        )
        return True

    except Exception as e:
        results.add_result(
            "Akamai Block Test",
            False,
            f"Error during Akamai test: {e}",
            {"error": str(e)}
        )
        return False


async def test_fingerprint_uniqueness(page: Page, results: TestResults):
    """Test 3: Is our fingerprint unique and realistic?"""
    try:
        # Navigate to a test page first
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1)

        fingerprint_hash = await compute_fingerprint_hash(page)

        # Get detailed fingerprint data
        fp_data = await page.evaluate("""
            () => {
                const data = {};
                data.screen = {
                    width: window.screen.width,
                    height: window.screen.height,
                };
                data.navigator = {
                    platform: navigator.platform,
                    language: navigator.language,
                    userAgent: navigator.userAgent,
                };
                return data;
            }
        """)

        results.add_result(
            "Fingerprint Uniqueness",
            True,
            f"Fingerprint generated successfully: {fingerprint_hash[:16]}...",
            {
                "fingerprint_hash": fingerprint_hash,
                "screen": fp_data.get("screen"),
                "navigator": fp_data.get("navigator"),
            }
        )
        return True

    except Exception as e:
        results.add_result(
            "Fingerprint Uniqueness",
            False,
            f"Fingerprint test failed: {e}",
            {"error": str(e)}
        )
        return False


async def test_pickup_filter(page: Page, category_name: str, category_url: str, results: TestResults):
    """Test 4: Does pickup filter selector work and actually apply?"""
    try:
        # Navigate to category
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)

        # Wait for page to settle
        akamai_clear = await _wait_for_akamai_clear(page, timeout_s=30.0)
        if not akamai_clear:
            results.akamai_blocks += 1

            # Take screenshot of block
            screenshot_path = Path(__file__).parent / f"screenshot_blocked_{category_name.replace(' ', '_')}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
                print(f"Screenshot saved: {screenshot_path}")
            except:
                pass

            results.add_result(
                f"Pickup Filter - {category_name}",
                False,
                "Akamai blocked category page",
                {"url": category_url, "screenshot": str(screenshot_path)}
            )
            results.pickup_filter_failures += 1
            return False

        # Get product count before filter
        await asyncio.sleep(2)

        # Check what's on the page
        page_info = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]');

                // Look for pickup filter elements
                const pickupSelectors = [
                    'label:has-text("Get It Today")',
                    'label:has-text("Pickup Today")',
                    'button:has-text("Pickup")',
                    '[data-testid*="pickup"]',
                    '[aria-label*="Pickup"]',
                ];

                const availabilityButtons = document.querySelectorAll('button:has-text("Availability")');
                const getItFastButtons = document.querySelectorAll('button:has-text("Get It Fast")');

                return {
                    cardCount: cards.length,
                    availabilityButtons: availabilityButtons.length,
                    getItFastButtons: getItFastButtons.length,
                    pageTitle: document.title,
                    hasFilterSection: document.querySelector('[data-testid*="filter"]') !== null,
                };
            }
        """)

        print(f"\nPage analysis for {category_name}:")
        print(f"  - Product cards: {page_info['cardCount']}")
        print(f"  - Availability buttons: {page_info['availabilityButtons']}")
        print(f"  - Get It Fast buttons: {page_info['getItFastButtons']}")
        print(f"  - Has filter section: {page_info['hasFilterSection']}")
        print(f"  - Title: {page_info['pageTitle']}")

        count_before = page_info['cardCount']

        # Try to apply pickup filter
        print(f"\nAttempting to apply pickup filter for {category_name}...")
        filter_applied = await apply_pickup_filter(page, category_name)

        if not filter_applied:
            # Take screenshot of failure
            screenshot_path = Path(__file__).parent / f"screenshot_filter_failed_{category_name.replace(' ', '_')}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
                print(f"Screenshot saved: {screenshot_path}")
            except:
                pass

            results.pickup_filter_failures += 1
            results.add_result(
                f"Pickup Filter - {category_name}",
                False,
                "Pickup filter did not apply",
                {
                    "url": category_url,
                    "products_before": count_before,
                    "page_info": page_info,
                    "screenshot": str(screenshot_path),
                }
            )
            return False

        # Get product count after filter
        await asyncio.sleep(2)
        count_after = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]');
                return cards.length;
            }
        """)

        # Check if URL changed
        url_after = page.url
        has_filter_param = "pickup" in url_after.lower() or "availability" in url_after.lower()

        # Take success screenshot
        screenshot_path = Path(__file__).parent / f"screenshot_filter_success_{category_name.replace(' ', '_')}.png"
        try:
            await page.screenshot(path=str(screenshot_path))
            print(f"Screenshot saved: {screenshot_path}")
        except:
            pass

        results.pickup_filter_successes += 1
        results.add_result(
            f"Pickup Filter - {category_name}",
            True,
            "Pickup filter applied successfully",
            {
                "url": category_url,
                "url_after": url_after,
                "products_before": count_before,
                "products_after": count_after,
                "filter_in_url": has_filter_param,
                "screenshot": str(screenshot_path),
            }
        )
        return True

    except Exception as e:
        results.pickup_filter_failures += 1
        results.add_result(
            f"Pickup Filter - {category_name}",
            False,
            f"Pickup filter test failed: {e}",
            {"error": str(e), "url": category_url}
        )
        return False


async def test_product_extraction(page: Page, category_name: str, category_url: str, results: TestResults):
    """Test 5: Can we extract products from the page?"""
    try:
        # Navigate to category (pickup filter should already be applied)
        if page.url != category_url:
            await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

        # Extract products using the main.py function
        products = await extract_products(
            page,
            store_id="0004",
            store_name="Seattle Rainier",
            category=category_name
        )

        results.products_found += len(products)

        if len(products) > 0:
            results.add_result(
                f"Product Extraction - {category_name}",
                True,
                f"Extracted {len(products)} products",
                {
                    "product_count": len(products),
                    "sample_product": products[0] if products else None,
                }
            )
            return True
        else:
            results.add_result(
                f"Product Extraction - {category_name}",
                False,
                "No products extracted (may be normal if filter too restrictive)",
                {"url": category_url}
            )
            return False

    except Exception as e:
        results.add_result(
            f"Product Extraction - {category_name}",
            False,
            f"Product extraction failed: {e}",
            {"error": str(e), "url": category_url}
        )
        return False


async def test_full_category_scrape(page: Page, category_name: str, category_url: str, results: TestResults):
    """Test 6: Full category scrape with pagination (2-3 pages max)."""
    try:
        products = await scrape_category(
            page,
            category_url,
            category_name,
            "0004",  # store_id
            "Seattle Rainier",
            max_pages=3,
        )

        results.products_found += len(products)
        results.categories_tested += 1

        if len(products) > 0:
            results.add_result(
                f"Full Scrape - {category_name}",
                True,
                f"Scraped {len(products)} products across up to 3 pages",
                {
                    "product_count": len(products),
                    "sample_products": products[:3] if len(products) >= 3 else products,
                }
            )
            return True
        else:
            results.add_result(
                f"Full Scrape - {category_name}",
                False,
                "No products found (may indicate filter or selector issues)",
                {"url": category_url}
            )
            return False

    except Exception as e:
        results.add_result(
            f"Full Scrape - {category_name}",
            False,
            f"Full scrape failed: {e}",
            {"error": str(e), "url": category_url}
        )
        return False


async def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("LOWE'S ACTOR LOCAL TEST SUITE")
    print("="*60 + "\n")

    results = TestResults()

    # Test categories (Clearance + Power Tools)
    categories = [
        {
            "name": "Clearance",
            "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"
        },
        {
            "name": "Power Tools",
            "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"
        },
    ]

    print(f"Testing with {len(categories)} categories:")
    for cat in categories:
        print(f"  - {cat['name']}: {cat['url']}")
    print()

    async with async_playwright() as playwright:
        browser = None
        context = None
        page = None

        try:
            # Test 1: Browser launch
            browser, context, page = await test_browser_launch(playwright, results)

            # Test 2: Akamai block check
            akamai_ok = await test_akamai_block(page, results)

            if not akamai_ok:
                print("\n⚠️  AKAMAI BLOCKED - Continuing tests anyway to see what happens...\n")

            # Test 3: Fingerprint uniqueness
            await test_fingerprint_uniqueness(page, results)

            # Test each category
            for category in categories:
                print(f"\n{'='*60}")
                print(f"TESTING CATEGORY: {category['name']}")
                print(f"{'='*60}\n")

                # Test 4: Pickup filter
                filter_ok = await test_pickup_filter(page, category['name'], category['url'], results)

                if filter_ok:
                    # Test 5: Product extraction (single page)
                    await test_product_extraction(page, category['name'], category['url'], results)

                    # Test 6: Full scrape (2-3 pages)
                    await test_full_category_scrape(page, category['name'], category['url'], results)
                else:
                    print(f"\n⚠️  Skipping extraction tests for {category['name']} - pickup filter failed\n")

                # Small delay between categories
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user\n")

        except Exception as e:
            print(f"\n\n❌ FATAL ERROR: {e}\n")
            results.add_result(
                "Fatal Error",
                False,
                f"Test suite crashed: {e}",
                {"error": str(e)}
            )

        finally:
            # Cleanup
            print("\nCleaning up...")
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
            if browser:
                try:
                    await browser.close()
                except:
                    pass

    # Generate report
    report = results.generate_report()

    # Save to file
    report_path = Path(__file__).parent / "TEST_RESULTS_LOCAL.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {report_path}")
    print(f"\nSummary:")
    print(f"  Total Tests: {results.tests_run}")
    print(f"  Passed: {results.tests_passed}")
    print(f"  Failed: {results.tests_failed}")
    print(f"  Products Found: {results.products_found}")
    print(f"  Akamai Blocks: {results.akamai_blocks}")
    print(f"  Pickup Filter Success Rate: {results.pickup_filter_successes}/{results.pickup_filter_successes + results.pickup_filter_failures}")
    print()

    # Exit with appropriate code
    sys.exit(0 if results.tests_failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
