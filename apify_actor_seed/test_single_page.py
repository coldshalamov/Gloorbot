"""
Minimal Test: Single Page Scrape

The simplest possible test - scrape ONE page and see what we get.
Great for debugging and quick validation.

Usage:
    python test_single_page.py
    python test_single_page.py --url "https://www.lowes.com/pl/..."
    python test_single_page.py --headless
"""

import argparse
import asyncio
import json
import random
import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


# Default test URL - lumber category (always has products)
DEFAULT_URL = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"


async def extract_products_simple(page: Any) -> list[dict]:
    """Simple product extraction - just get what's visible."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # Try JSON-LD first
    try:
        scripts = await page.query_selector_all("script[type='application/ld+json']")
        for script in scripts:
            try:
                raw = await script.inner_text()
                data = json.loads(raw)

                # Find product objects
                def find_products(obj):
                    found = []
                    if isinstance(obj, dict):
                        if obj.get("@type", "").lower() == "product":
                            found.append(obj)
                        for v in obj.values():
                            found.extend(find_products(v))
                    elif isinstance(obj, list):
                        for item in obj:
                            found.extend(find_products(item))
                    return found

                for prod in find_products(data):
                    offers = prod.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}

                    price_str = str(offers.get("price", ""))
                    price_match = re.search(r'(\d+\.?\d*)', price_str)
                    price = float(price_match.group(1)) if price_match else None

                    if price:
                        products.append({
                            "sku": prod.get("sku"),
                            "title": prod.get("name", "")[:100],
                            "price": price,
                            "url": offers.get("url") or prod.get("url"),
                            "source": "json-ld",
                            "timestamp": timestamp,
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"JSON-LD extraction error: {e}")

    # Try DOM extraction
    try:
        cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
        print(f"Found {len(cards)} product cards in DOM")

        for card in cards[:10]:  # Limit to first 10 for testing
            try:
                # Get title
                title_el = await card.query_selector("a[href*='/pd/'], h3, h2")
                title = await title_el.inner_text() if title_el else None

                # Get price
                price_el = await card.query_selector("[data-test*='price'], [aria-label*='$']")
                price_text = await price_el.inner_text() if price_el else None
                price_match = re.search(r'(\d+\.?\d*)', price_text or "")
                price = float(price_match.group(1)) if price_match else None

                # Get link
                link_el = await card.query_selector("a[href*='/pd/']")
                href = await link_el.get_attribute("href") if link_el else None

                # Extract SKU from URL
                sku = None
                if href:
                    sku_match = re.search(r'/pd/[^/]+-(\d+)', href)
                    sku = sku_match.group(1) if sku_match else None

                if title and price:
                    # Check if we already have this from JSON-LD
                    if not any(p.get("sku") == sku for p in products):
                        products.append({
                            "sku": sku,
                            "title": title[:100],
                            "price": price,
                            "url": f"https://www.lowes.com{href}" if href else None,
                            "source": "dom",
                            "timestamp": timestamp,
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"DOM extraction error: {e}")

    return products


async def main(url: str, headless: bool = False):
    print("=" * 60)
    print("SINGLE PAGE SCRAPE TEST")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"Headless: {headless}")
    print()

    async with async_playwright() as playwright:
        # Launch browser
        print("Launching browser...")
        browser = await playwright.chromium.launch(
            headless=headless,
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
            # Navigate
            print(f"Navigating to page...")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            print(f"Response status: {response.status if response else 'N/A'}")

            # Check for blocks
            content = await page.content()
            if "Access Denied" in content:
                print("BLOCKED by Akamai!")
                return

            if "Aw, Snap!" in content:
                print("Page crashed!")
                return

            # Wait for page to load
            print("Waiting for network idle...")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                print("Network idle timeout, continuing...")

            await asyncio.sleep(2)

            # Get page info
            title = await page.title()
            print(f"Page title: {title}")

            # Try to find and click pickup filter
            print("\nLooking for pickup filter...")
            pickup_selectors = [
                'label:has-text("Get It Today")',
                'label:has-text("Pickup Today")',
                'button:has-text("Pickup")',
                '[aria-label*="Pickup"]',
            ]

            filter_found = False
            for sel in pickup_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        text = await el.inner_text()
                        print(f"  Found: '{text[:50]}' via {sel}")
                        filter_found = True

                        # Click it
                        await el.click()
                        print("  Clicked!")
                        await asyncio.sleep(2)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except Exception:
                            pass
                        break
                except Exception:
                    continue

            if not filter_found:
                print("  Pickup filter NOT FOUND")

            # Extract products
            print("\nExtracting products...")
            products = await extract_products_simple(page)

            print(f"\nFound {len(products)} products:")
            for i, p in enumerate(products[:5]):  # Show first 5
                print(f"  {i+1}. {p.get('title', 'N/A')[:50]}... - ${p.get('price', 'N/A')}")

            if len(products) > 5:
                print(f"  ... and {len(products) - 5} more")

            # Save results
            output_file = "test_single_page_output.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=2)
            print(f"\nResults saved to: {output_file}")

            # Take screenshot
            screenshot_file = "test_single_page_screenshot.png"
            await page.screenshot(path=screenshot_file, full_page=False)
            print(f"Screenshot saved to: {screenshot_file}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="URL to scrape")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.headless))
