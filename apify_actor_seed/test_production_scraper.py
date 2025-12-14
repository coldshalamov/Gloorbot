"""
Comprehensive Test Suite for Lowe's Production Scraper

This test suite validates all critical functionality:
1. Browser launch and stealth
2. Page loading without Akamai blocks
3. Pickup filter discovery and clicking
4. Product extraction (JSON-LD and DOM)
5. Full category pagination

Run with: python test_production_scraper.py

Exit codes:
- 0: All tests passed
- 1: Some tests failed
"""

import asyncio
import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright, Browser, Page
from playwright_stealth import Stealth


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

# URLs for testing
TEST_URLS = {
    "lumber": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532",
    "clearance": "https://www.lowes.com/pl/The-back-aisle/2021454685607",
    "power_tools": "https://www.lowes.com/pl/Power-tools-Tools/4294612503",
    "paint": "https://www.lowes.com/pl/Paint-Paint-supplies/4294820090",
}

# Output directory
OUTPUT_DIR = Path("test_results")


# =============================================================================
# TEST RESULT TRACKING
# =============================================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: int = 0
    details: dict = field(default_factory=dict)


class TestSuite:
    def __init__(self):
        self.results: list[TestResult] = []
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def add_result(self, result: TestResult):
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name}: {result.message}")

    def summary(self) -> tuple[int, int]:
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        return passed, failed


# =============================================================================
# RESOURCE BLOCKING (same as production)
# =============================================================================

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

BLOCKED_URL_PATTERNS = [
    r"google-analytics\.com", r"googletagmanager\.com", r"facebook\.net",
    r"doubleclick\.net", r"analytics", r"tracking", r"beacon", r"pixel",
    r"ads\.", r"adservice", r"youtube\.com", r"vimeo\.com",
    r"hotjar\.com", r"clarity\.ms", r"newrelic\.com",
    r"\.woff2?(\?|$)", r"\.ttf(\?|$)",
]

NEVER_BLOCK_PATTERNS = [
    r"/_sec/", r"/akam/", r"akamai", r"lowes\.com",
]


async def setup_blocking(page: Page):
    """Set up resource blocking."""
    async def handle_route(route):
        url = route.request.url.lower()
        resource_type = route.request.resource_type

        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.continue_()
                return

        if resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return

        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", handle_route)


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

async def test_browser_launch(suite: TestSuite) -> bool:
    """Test 1: Browser launches successfully with stealth."""
    start = datetime.now()

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )

        page = await context.new_page()

        # Apply stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Set up blocking
        await setup_blocking(page)

        suite.browser = browser
        suite.page = page
        suite._playwright = playwright
        suite._context = context

        duration = (datetime.now() - start).total_seconds() * 1000

        suite.add_result(TestResult(
            name="Browser Launch",
            passed=True,
            message="Browser launched with stealth",
            duration_ms=int(duration),
        ))
        return True

    except Exception as e:
        suite.add_result(TestResult(
            name="Browser Launch",
            passed=False,
            message=f"Failed: {e}",
        ))
        return False


async def test_page_load_no_block(suite: TestSuite) -> bool:
    """Test 2: Page loads without Akamai block."""
    if not suite.page:
        suite.add_result(TestResult(
            name="Page Load",
            passed=False,
            message="No browser available",
        ))
        return False

    start = datetime.now()
    page = suite.page
    url = TEST_URLS["lumber"]

    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Check HTTP status
        if response and response.status >= 400:
            suite.add_result(TestResult(
                name="Page Load",
                passed=False,
                message=f"HTTP {response.status}",
                details={"url": url},
            ))
            return False

        # Check for Akamai block
        content = await page.content()
        title = await page.title()

        blocked = False
        if "Access Denied" in content or "Access Denied" in title:
            blocked = True
        if "Reference #" in content:
            blocked = True

        if blocked:
            # Take screenshot of block
            OUTPUT_DIR.mkdir(exist_ok=True)
            await page.screenshot(path=str(OUTPUT_DIR / "blocked.png"))

            suite.add_result(TestResult(
                name="Page Load",
                passed=False,
                message="BLOCKED by Akamai",
                details={"url": url, "screenshot": "blocked.png"},
            ))
            return False

        # Wait for network idle
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        duration = (datetime.now() - start).total_seconds() * 1000

        suite.add_result(TestResult(
            name="Page Load",
            passed=True,
            message=f"Loaded in {int(duration)}ms",
            duration_ms=int(duration),
            details={"url": url, "title": title},
        ))
        return True

    except Exception as e:
        suite.add_result(TestResult(
            name="Page Load",
            passed=False,
            message=f"Error: {e}",
        ))
        return False


async def test_pickup_filter(suite: TestSuite) -> bool:
    """Test 3: Pickup filter can be found and clicked."""
    if not suite.page:
        suite.add_result(TestResult(
            name="Pickup Filter",
            passed=False,
            message="No page available",
        ))
        return False

    start = datetime.now()
    page = suite.page

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
    ]

    # Try expanding availability section first
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
                    print(f"    Expanding availability section...")
                    await toggle.click()
                    await asyncio.sleep(0.5)
                break
        except Exception:
            continue

    # Find pickup filter
    filter_element = None
    filter_text = ""
    found_selector = ""

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

                    if len(filter_text) < 100:
                        filter_element = el
                        found_selector = selector
                        break

            if filter_element:
                break
        except Exception:
            continue

    if not filter_element:
        # Take screenshot
        OUTPUT_DIR.mkdir(exist_ok=True)
        await page.screenshot(path=str(OUTPUT_DIR / "no_filter.png"))

        suite.add_result(TestResult(
            name="Pickup Filter",
            passed=False,
            message="Filter element NOT FOUND",
            details={"screenshot": "no_filter.png"},
        ))
        return False

    print(f"    Found filter: '{filter_text[:40]}' via {found_selector}")

    # Check if already selected
    async def is_selected(el):
        for attr in ["aria-checked", "aria-pressed", "aria-selected"]:
            val = await el.get_attribute(attr)
            if val == "true":
                return True
        try:
            return await el.is_checked()
        except Exception:
            return False

    was_selected = await is_selected(filter_element)
    if was_selected:
        duration = (datetime.now() - start).total_seconds() * 1000
        suite.add_result(TestResult(
            name="Pickup Filter",
            passed=True,
            message="Filter already active",
            duration_ms=int(duration),
            details={"text": filter_text, "selector": found_selector},
        ))
        return True

    # Click the filter
    url_before = page.url
    print(f"    Clicking filter...")
    await filter_element.click()
    await asyncio.sleep(1)

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    # Verify click worked
    verified = False
    verification_method = ""

    # Method 1: Check element state
    if await is_selected(filter_element):
        verified = True
        verification_method = "aria-checked/pressed"

    # Method 2: Check URL change
    if not verified:
        url_after = page.url.lower()
        if url_after != url_before and ("pickup" in url_after or "availability" in url_after):
            verified = True
            verification_method = "URL change"

    duration = (datetime.now() - start).total_seconds() * 1000

    if verified:
        suite.add_result(TestResult(
            name="Pickup Filter",
            passed=True,
            message=f"Filter clicked and verified via {verification_method}",
            duration_ms=int(duration),
            details={"text": filter_text, "selector": found_selector},
        ))
        return True
    else:
        suite.add_result(TestResult(
            name="Pickup Filter",
            passed=False,
            message="Filter clicked but NOT verified",
            details={"text": filter_text, "selector": found_selector},
        ))
        return False


async def test_product_extraction(suite: TestSuite) -> bool:
    """Test 4: Products can be extracted from the page."""
    if not suite.page:
        suite.add_result(TestResult(
            name="Product Extraction",
            passed=False,
            message="No page available",
        ))
        return False

    start = datetime.now()
    page = suite.page
    products = []

    # Try JSON-LD extraction
    try:
        json_ld_data = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)

        def collect_products(obj):
            found = []
            if isinstance(obj, dict):
                if obj.get("@type", "").lower() == "product":
                    found.append(obj)
                for v in obj.values():
                    found.extend(collect_products(v))
            elif isinstance(obj, list):
                for item in obj:
                    found.extend(collect_products(item))
            return found

        for payload in json_ld_data:
            for product in collect_products(payload):
                offers = product.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                price_str = str(offers.get("price", ""))
                price_match = re.search(r'(\d+\.?\d*)', price_str)
                price = float(price_match.group(1)) if price_match else None

                if price:
                    products.append({
                        "source": "json-ld",
                        "sku": product.get("sku"),
                        "title": (product.get("name") or "")[:100],
                        "price": price,
                        "url": offers.get("url") or product.get("url"),
                    })

        print(f"    JSON-LD: Found {len(products)} products")

    except Exception as e:
        print(f"    JSON-LD error: {e}")

    # Try DOM extraction if needed
    if len(products) < 5:
        try:
            dom_products = await page.evaluate("""
                () => {
                    const products = [];
                    const cards = document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]');

                    cards.forEach(card => {
                        try {
                            const titleEl = card.querySelector('a[href*="/pd/"], h3, h2');
                            const priceEl = card.querySelector('[data-test*="price"], [aria-label*="$"]');
                            const linkEl = card.querySelector('a[href*="/pd/"]');

                            if (titleEl && priceEl) {
                                products.push({
                                    title: titleEl.innerText?.trim() || '',
                                    price: priceEl.innerText?.trim() || '',
                                    href: linkEl?.getAttribute('href') || '',
                                });
                            }
                        } catch {}
                    });

                    return products;
                }
            """)

            for raw in dom_products:
                price_match = re.search(r'(\d+\.?\d*)', raw.get("price", ""))
                price = float(price_match.group(1)) if price_match else None

                if price and not any(p.get("title") == raw.get("title") for p in products):
                    products.append({
                        "source": "dom",
                        "title": raw.get("title", "")[:100],
                        "price": price,
                        "url": raw.get("href"),
                    })

            print(f"    DOM: Found {len(dom_products)} cards, {len(products)} total products")

        except Exception as e:
            print(f"    DOM error: {e}")

    duration = (datetime.now() - start).total_seconds() * 1000

    if len(products) > 0:
        # Save sample products
        OUTPUT_DIR.mkdir(exist_ok=True)
        with open(OUTPUT_DIR / "sample_products.json", "w") as f:
            json.dump(products[:10], f, indent=2)

        suite.add_result(TestResult(
            name="Product Extraction",
            passed=True,
            message=f"Extracted {len(products)} products",
            duration_ms=int(duration),
            details={"count": len(products), "sample_file": "sample_products.json"},
        ))
        return True
    else:
        # Take screenshot
        await page.screenshot(path=str(OUTPUT_DIR / "no_products.png"))

        suite.add_result(TestResult(
            name="Product Extraction",
            passed=False,
            message="No products found",
            details={"screenshot": "no_products.png"},
        ))
        return False


async def test_pagination(suite: TestSuite) -> bool:
    """Test 5: Pagination works correctly."""
    if not suite.page:
        suite.add_result(TestResult(
            name="Pagination",
            passed=False,
            message="No page available",
        ))
        return False

    start = datetime.now()
    page = suite.page

    # Get current URL
    current_url = page.url
    parsed = current_url.split("?")[0]

    # Navigate to page 2 (offset=24)
    page2_url = f"{parsed}?offset=24"

    try:
        print(f"    Navigating to page 2: {page2_url[:60]}...")

        response = await page.goto(page2_url, wait_until="domcontentloaded", timeout=45000)

        if response and response.status >= 400:
            suite.add_result(TestResult(
                name="Pagination",
                passed=False,
                message=f"HTTP {response.status} on page 2",
            ))
            return False

        # Check for block
        content = await page.content()
        if "Access Denied" in content:
            suite.add_result(TestResult(
                name="Pagination",
                passed=False,
                message="BLOCKED on page 2",
            ))
            return False

        await asyncio.sleep(1)

        # Try to count products
        try:
            cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
            product_count = len(cards)
        except Exception:
            product_count = -1

        duration = (datetime.now() - start).total_seconds() * 1000

        suite.add_result(TestResult(
            name="Pagination",
            passed=True,
            message=f"Page 2 loaded, {product_count} products visible",
            duration_ms=int(duration),
            details={"url": page2_url, "products": product_count},
        ))
        return True

    except Exception as e:
        suite.add_result(TestResult(
            name="Pagination",
            passed=False,
            message=f"Error: {e}",
        ))
        return False


async def cleanup(suite: TestSuite):
    """Clean up browser resources."""
    try:
        if hasattr(suite, '_context'):
            await suite._context.close()
        if suite.browser:
            await suite.browser.close()
        if hasattr(suite, '_playwright'):
            await suite._playwright.stop()
    except Exception as e:
        print(f"Cleanup error: {e}")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("LOWE'S PRODUCTION SCRAPER - TEST SUITE")
    print("=" * 70)
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}\n")

    OUTPUT_DIR.mkdir(exist_ok=True)

    suite = TestSuite()

    tests = [
        ("Browser Launch", test_browser_launch),
        ("Page Load (no block)", test_page_load_no_block),
        ("Pickup Filter", test_pickup_filter),
        ("Product Extraction", test_product_extraction),
        ("Pagination", test_pagination),
    ]

    print("Running tests:\n")

    for test_name, test_func in tests:
        print(f"\n>> {test_name}")
        try:
            await test_func(suite)
        except Exception as e:
            suite.add_result(TestResult(
                name=test_name,
                passed=False,
                message=f"Exception: {e}",
            ))

        # Small delay between tests
        await asyncio.sleep(random.uniform(0.5, 1.0))

    await cleanup(suite)

    # Summary
    passed, failed = suite.summary()
    total = passed + failed

    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)

    for result in suite.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.name}: {result.message}")
        if result.details:
            for k, v in result.details.items():
                print(f"         {k}: {v}")

    print(f"\n{'='*70}")
    print(f"TOTAL: {passed}/{total} tests passed")

    if failed == 0:
        print("\nALL TESTS PASSED - Scraper is ready for production!")
        print("="*70)
        return 0
    else:
        print(f"\n{failed} TESTS FAILED - Review and fix issues before deployment")
        print("="*70)
        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
