"""
Local Test Runner for Lowe's Scraper

Tests the Actor logic WITHOUT Apify cloud - runs entirely on your machine.
Uses a mock Actor class that simulates Apify's API locally.

Usage:
    python test_local.py                    # Quick test (1 store, 1 category, 1 page)
    python test_local.py --full             # Full test (3 stores, 5 categories, 2 pages)
    python test_local.py --store 0061       # Test specific store
    python test_local.py --no-proxy         # Skip proxy (direct connection)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


class MockActorLog:
    """Mock Actor.log that prints to console."""

    @staticmethod
    def info(msg: str, *args, **kwargs):
        print(f"[INFO] {msg}")

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        print(f"[WARN] {msg}")

    @staticmethod
    def error(msg: str, *args, **kwargs):
        print(f"[ERROR] {msg}")

    @staticmethod
    def debug(msg: str, *args, **kwargs):
        if os.getenv("DEBUG"):
            print(f"[DEBUG] {msg}")


class MockRequest:
    """Mock Apify Request object."""

    def __init__(self, url: str, user_data: dict):
        self.url = url
        self.user_data = user_data

    @classmethod
    def from_url(cls, url: str, user_data: dict = None):
        return cls(url, user_data or {})


class MockRequestQueue:
    """Mock Apify Request Queue - uses a simple list."""

    def __init__(self):
        self.requests: list[MockRequest] = []
        self.handled: set[str] = set()
        self.index = 0

    async def add_request(self, request: MockRequest):
        self.requests.append(request)

    async def fetch_next_request(self) -> MockRequest | None:
        while self.index < len(self.requests):
            request = self.requests[self.index]
            self.index += 1
            if request.url not in self.handled:
                return request
        return None

    async def mark_request_as_handled(self, request: MockRequest):
        self.handled.add(request.url)

    async def reclaim_request(self, request: MockRequest):
        # Put back at end of queue
        self.requests.append(request)


class MockProxyConfiguration:
    """Mock proxy configuration - returns None (direct connection)."""

    def __init__(self, use_proxy: bool = False):
        self.use_proxy = use_proxy

    async def new_url(self, session_id: str = None) -> str | None:
        if not self.use_proxy:
            return None
        # Return a placeholder - you'd need real proxy credentials
        return None


class MockDataset:
    """Mock Dataset - saves to local JSON file."""

    def __init__(self, output_file: str = "test_output.json"):
        self.output_file = output_file
        self.data: list[dict] = []

    async def push_data(self, items: list[dict] | dict):
        if isinstance(items, dict):
            items = [items]
        self.data.extend(items)

        # Save incrementally
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, default=str)

        print(f"[DATA] Saved {len(items)} items (total: {len(self.data)})")


class MockActor:
    """Mock Actor class that simulates Apify's Actor API locally."""

    log = MockActorLog()
    _input: dict = {}
    _dataset: MockDataset = None
    _request_queue: MockRequestQueue = None
    _proxy_config: MockProxyConfiguration = None

    @classmethod
    def set_input(cls, input_data: dict):
        cls._input = input_data

    @classmethod
    async def get_input(cls) -> dict:
        return cls._input

    @classmethod
    async def open_request_queue(cls) -> MockRequestQueue:
        if cls._request_queue is None:
            cls._request_queue = MockRequestQueue()
        return cls._request_queue

    @classmethod
    async def create_proxy_configuration(cls, groups: list = None, country_code: str = None) -> MockProxyConfiguration:
        if cls._proxy_config is None:
            cls._proxy_config = MockProxyConfiguration(use_proxy=False)
        return cls._proxy_config

    @classmethod
    async def push_data(cls, items: list[dict] | dict):
        if cls._dataset is None:
            cls._dataset = MockDataset()
        await cls._dataset.push_data(items)

    @classmethod
    async def exit(cls):
        pass

    @classmethod
    def reset(cls):
        """Reset state between test runs."""
        cls._input = {}
        cls._dataset = None
        cls._request_queue = None
        cls._proxy_config = None


# Monkey-patch the apify module
class MockApifyModule:
    Actor = MockActor
    Request = MockRequest


sys.modules['apify'] = MockApifyModule()


async def run_local_test(
    store_ids: list[str] = None,
    categories: list[str] = None,
    max_pages: int = 1,
    use_proxy: bool = False,
    headless: bool = False,
):
    """Run the scraper locally with mock Apify components."""

    print("=" * 60)
    print("LOCAL TEST MODE - No Apify cloud costs!")
    print("=" * 60)

    # Reset mock state
    MockActor.reset()

    # Default test configuration
    if store_ids is None:
        # Just test one store
        store_ids = ["0061"]  # Arlington, WA

    if categories is None:
        # Just test one category with products
        categories = [
            "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"
        ]

    # Set mock input
    MockActor.set_input({
        "store_ids": store_ids,
        "categories": categories,
        "max_pages_per_category": max_pages,
        "use_stealth": True,
        "proxy_country": "US",
    })

    # Configure proxy mock
    MockActor._proxy_config = MockProxyConfiguration(use_proxy=use_proxy)

    print(f"\nTest Configuration:")
    print(f"  Stores: {store_ids}")
    print(f"  Categories: {len(categories)}")
    print(f"  Max Pages: {max_pages}")
    print(f"  Use Proxy: {use_proxy}")
    print(f"  Headless: {headless}")
    print()

    # Import and run the main function
    # We need to modify main.py to accept headless parameter
    from src.main import (
        parse_store_ids_from_lowesmap,
        parse_categories_from_lowesmap,
        build_category_url,
        apply_pickup_filter,
        extract_products,
        check_for_crash,
        check_for_akamai_block,
        PAGE_SIZE,
        GOTO_TIMEOUT_MS,
        BASE_URL,
    )
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
    import random

    # Get input
    actor_input = await MockActor.get_input()
    input_store_ids = actor_input.get("store_ids", [])
    input_categories = actor_input.get("categories", [])
    max_pages = actor_input.get("max_pages_per_category", 1)

    # Build stores list
    stores = [{"store_id": sid, "store_name": f"Store {sid}"} for sid in input_store_ids]

    # Build categories list
    categories_list = [{"name": f"Category {i}", "url": url} for i, url in enumerate(input_categories)]

    # Open mock request queue
    request_queue = await MockActor.open_request_queue()

    # Enqueue URLs
    total_urls = len(stores) * len(categories_list) * max_pages
    print(f"Enqueueing {total_urls} URLs...")

    for store in stores:
        store_id = store["store_id"]
        store_name = store.get("store_name", f"Store {store_id}")

        for category in categories_list:
            category_name = category["name"]
            category_url = category["url"]

            for page_num in range(max_pages):
                offset = page_num * PAGE_SIZE
                url = build_category_url(category_url, store_id, offset)

                request = MockRequest.from_url(
                    url,
                    user_data={
                        "store_id": store_id,
                        "store_name": store_name,
                        "category_name": category_name,
                        "page_num": page_num,
                        "offset": offset,
                    }
                )
                await request_queue.add_request(request)

    print(f"Enqueued {len(request_queue.requests)} URLs. Starting browser...")

    # Process with Playwright
    async with async_playwright() as playwright:
        total_products = 0
        processed = 0

        # Launch browser ONCE (more efficient for local testing)
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
        await stealth_async(page)

        try:
            while True:
                request = await request_queue.fetch_next_request()
                if not request:
                    break

                store_id = request.user_data.get("store_id", "unknown")
                store_name = request.user_data.get("store_name", "Unknown Store")
                category_name = request.user_data.get("category_name", "Unknown")
                page_num = request.user_data.get("page_num", 0)

                try:
                    print(f"\n[{processed + 1}/{total_urls}] {store_name} | {category_name} | Page {page_num + 1}")
                    print(f"  URL: {request.url[:80]}...")

                    # Navigate
                    response = await page.goto(
                        request.url,
                        wait_until="domcontentloaded",
                        timeout=GOTO_TIMEOUT_MS,
                    )

                    if response and response.status >= 400:
                        print(f"  HTTP {response.status} - skipping")
                        await request_queue.mark_request_as_handled(request)
                        processed += 1
                        continue

                    # Check for blocks
                    if await check_for_crash(page):
                        print("  Page crashed!")
                        continue

                    if await check_for_akamai_block(page):
                        print("  AKAMAI BLOCKED!")
                        await asyncio.sleep(5)
                        continue

                    # Wait for page
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass

                    # Apply pickup filter
                    pickup_applied = await apply_pickup_filter(page, category_name)
                    print(f"  Pickup filter: {'Applied' if pickup_applied else 'NOT FOUND'}")

                    # Extract products
                    products = await extract_products(page, store_id, store_name, category_name)

                    if products:
                        await MockActor.push_data(products)
                        total_products += len(products)
                        print(f"  Found {len(products)} products")
                    else:
                        print(f"  No products found")

                    await request_queue.mark_request_as_handled(request)
                    processed += 1

                    # Small delay
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                except Exception as e:
                    print(f"  ERROR: {e}")
                    await request_queue.mark_request_as_handled(request)
                    processed += 1

        finally:
            await browser.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print(f"Requests processed: {processed}")
    print(f"Products found: {total_products}")
    print(f"Output saved to: test_output.json")

    return total_products


def main():
    parser = argparse.ArgumentParser(description="Local test runner for Lowe's scraper")
    parser.add_argument("--full", action="store_true", help="Run full test (3 stores, 5 categories)")
    parser.add_argument("--store", type=str, help="Test specific store ID")
    parser.add_argument("--stores", type=str, help="Comma-separated store IDs")
    parser.add_argument("--category", type=str, help="Test specific category URL")
    parser.add_argument("--pages", type=int, default=1, help="Max pages per category")
    parser.add_argument("--no-proxy", action="store_true", help="Skip proxy (direct connection)")
    parser.add_argument("--headless", action="store_true", help="Run headless (may get blocked)")

    args = parser.parse_args()

    # Build configuration
    store_ids = None
    categories = None
    max_pages = args.pages

    if args.full:
        # Full test - multiple stores and categories
        store_ids = ["0061", "1089", "0252"]  # Arlington, Auburn, Seattle
        categories = [
            "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532",
            "https://www.lowes.com/pl/Hand-tools-Tools/4294612504",
            "https://www.lowes.com/pl/Power-tools-Tools/4294612503",
            "https://www.lowes.com/pl/Fasteners-Hardware/4294850541",
            "https://www.lowes.com/pl/Electrical-wire-cable/4294722493",
        ]
        max_pages = 2
    elif args.store:
        store_ids = [args.store]
    elif args.stores:
        store_ids = [s.strip() for s in args.stores.split(",")]

    if args.category:
        categories = [args.category]

    # Run test
    asyncio.run(run_local_test(
        store_ids=store_ids,
        categories=categories,
        max_pages=max_pages,
        use_proxy=not args.no_proxy,
        headless=args.headless,
    ))


if __name__ == "__main__":
    main()
