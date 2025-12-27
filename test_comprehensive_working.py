"""
Comprehensive test using the WORKING approach from Cheapskater Debug
- Stealth via hook_playwright_context() BEFORE browser launch
- Default Chromium (NOT Chrome channel)
- No custom launch args
- No custom fingerprint injection
- Store context first
- Pickup filter params in URL
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

class TestResults:
    def __init__(self):
        self.tests = []
        self.products_found = 0
        self.categories_tested = 0
        self.pickup_filter_success = 0

    def add(self, name, passed, message, details=None):
        status = "PASS" if passed else "FAIL"
        self.tests.append({
            "name": name,
            "status": status,
            "message": message,
            "details": details or {}
        })
        print(f"\n[{status}] {name}")
        print(f"    {message}")
        if details:
            for k, v in details.items():
                print(f"    {k}: {v}")

    def summary(self):
        passed = sum(1 for t in self.tests if t["status"] == "PASS")
        total = len(self.tests)
        print(f"\n{'='*60}")
        print(f"RESULTS: {passed}/{total} tests passed")
        print(f"Products found: {self.products_found}")
        print(f"Categories tested: {self.categories_tested}")
        print(f"{'='*60}")


async def set_store_context(page, zip_code="98144"):
    """Set store context before scraping."""
    print(f"\nSetting store for ZIP {zip_code}...")

    # Load homepage
    await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    # Find and click store selector
    store_selectors = [
        'button:has-text("Set Store")',
        'button:has-text("My Store")',
        '[data-testid*="store"]',
    ]

    for selector in store_selectors:
        try:
            button = await page.wait_for_selector(selector, timeout=3000)
            if button:
                await button.click()
                await asyncio.sleep(1)
                break
        except:
            continue

    # Enter ZIP
    zip_selectors = ['input[name*="zip"]', 'input[id*="zip"]', 'input[placeholder*="ZIP"]']
    for selector in zip_selectors:
        try:
            zip_input = await page.wait_for_selector(selector, timeout=5000)
            if zip_input:
                await zip_input.fill(zip_code)
                await asyncio.sleep(0.5)
                await zip_input.press("Enter")
                await asyncio.sleep(3)
                print(f"Store context set for {zip_code}")
                return True
        except:
            continue

    return False


async def scrape_category(page, url, category_name, results):
    """Scrape a category page."""
    print(f"\n--- Scraping {category_name} ---")

    # Add pickup filter params (like working version)
    if "?" not in url:
        full_url = f"{url}?pickupType=pickupToday&availability=pickupToday&inStock=1&offset=0"
    else:
        full_url = f"{url}&pickupType=pickupToday&availability=pickupToday&inStock=1&offset=0"

    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)

        title = await page.title()

        # Check if blocked
        if "Access Denied" in title:
            results.add(
                f"Category: {category_name}",
                False,
                "Akamai blocked",
                {"url": url}
            )
            return []

        # Check for products
        product_cards = await page.query_selector_all('[data-test="product-pod"]')
        print(f"Found {len(product_cards)} product cards")

        if len(product_cards) == 0:
            results.add(
                f"Category: {category_name}",
                False,
                "No products found (filter may be too restrictive or page format changed)",
                {"url": url, "title": title}
            )
            return []

        # Extract product data
        products = []
        for i, card in enumerate(product_cards[:5]):  # Just first 5 for testing
            try:
                # Get title
                title_el = await card.query_selector("a[href*='/pd/']")
                title_text = await title_el.inner_text() if title_el else "Unknown"

                # Get price
                price_el = await card.query_selector("[data-testid*='price']")
                price_text = await price_el.inner_text() if price_el else "0"

                # Get URL
                href = await title_el.get_attribute("href") if title_el else ""

                products.append({
                    "title": title_text[:50],
                    "price": price_text,
                    "url": href[:80] if href else ""
                })
            except Exception as e:
                continue

        results.add(
            f"Category: {category_name}",
            True,
            f"Extracted {len(products)} products",
            {"total_cards": len(product_cards), "extracted": len(products)}
        )

        results.products_found += len(products)
        results.categories_tested += 1

        return products

    except Exception as e:
        results.add(
            f"Category: {category_name}",
            False,
            f"Error: {str(e)}",
            {"url": url}
        )
        return []


async def main():
    print("="*60)
    print("COMPREHENSIVE TEST - WORKING APPROACH")
    print("="*60)

    results = TestResults()

    # Test categories
    categories = [
        {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
        {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
        {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    ]

    async with async_playwright() as p:
        # CRITICAL: Apply stealth to Playwright instance BEFORE launching
        print("\nApplying stealth to Playwright instance...")
        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            stealth.hook_playwright_context(p)
            results.add("Stealth Setup", True, "playwright-stealth hooked to context")
        except Exception as e:
            results.add("Stealth Setup", False, f"Failed to apply stealth: {e}")
            return

        # Launch browser - SIMPLE, like working version
        print("Launching Chromium (NOT Chrome)...")
        browser = await p.chromium.launch(headless=False)

        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            # Test 1: Set store context
            store_ok = await set_store_context(page, "98144")
            results.add("Store Context", store_ok, "Set ZIP 98144" if store_ok else "Failed to set store")

            # Test 2-4: Scrape categories
            all_products = []
            for cat in categories:
                products = await scrape_category(page, cat["url"], cat["name"], results)
                all_products.extend(products)
                await asyncio.sleep(1)  # Small delay between categories

            # Save results
            if all_products:
                output_file = "test_results_working.json"
                with open(output_file, "w") as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "products": all_products,
                        "total": len(all_products)
                    }, f, indent=2)
                print(f"\nSaved {len(all_products)} products to {output_file}")

        finally:
            await page.screenshot(path="test_final_screenshot.png")
            await browser.close()

    results.summary()

    # Generate report
    report = f"""# Comprehensive Test Report - Working Approach

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Configuration
- Stealth: hook_playwright_context() before browser launch
- Browser: Default Chromium (NOT Chrome channel)
- Launch args: None (default)
- Fingerprint injection: None (playwright-stealth only)
- Store context: Yes (ZIP 98144)
- Pickup filter: URL params (pickupType=pickupToday&availability=pickupToday)

## Results Summary
- **Total tests:** {len(results.tests)}
- **Passed:** {sum(1 for t in results.tests if t['status'] == 'PASS')}
- **Failed:** {sum(1 for t in results.tests if t['status'] == 'FAIL')}
- **Products found:** {results.products_found}
- **Categories tested:** {results.categories_tested}

## Test Details

"""

    for test in results.tests:
        report += f"### {test['name']}\n"
        report += f"- **Status:** {test['status']}\n"
        report += f"- **Message:** {test['message']}\n"
        if test['details']:
            report += f"- **Details:** {json.dumps(test['details'], indent=2)}\n"
        report += "\n"

    with open("TEST_COMPREHENSIVE_REPORT.md", "w") as f:
        f.write(report)

    print(f"\nReport saved to TEST_COMPREHENSIVE_REPORT.md")


if __name__ == "__main__":
    asyncio.run(main())
