"""
Lowe's Full Catalog Scraper - WA/OR Stores with Local Markdowns

PROVEN WORKING APPROACH:
✅ Chrome channel - NOT Chromium
✅ Persistent browser profiles (one per store)
✅ Homepage warmup with human behavior
✅ NO playwright-stealth (red flag!)
✅ NO fingerprint injection (makes it worse!)

PURPOSE:
- Scrape entire product catalog from all WA/OR Lowe's stores
- Find local markdowns using "pickup today" filter
- Run parallel scraping across stores (<1 hour total)
- Support off-site residential proxies
"""

from __future__ import annotations

import asyncio
import re
import random
from datetime import datetime
from pathlib import Path

from apify import Actor
from playwright.async_api import async_playwright, Page, BrowserContext


# ============================================================================
# CONFIGURATION
# ============================================================================

LOWES_MAP_PATH = Path(__file__).parent.parent / "LowesMap.txt"
MAX_CONCURRENT_STORES = 5  # Run 5 stores in parallel for speed
PAGE_SIZE = 24  # Products per page


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_stores_and_categories():
    """Load stores and categories from LowesMap.txt"""
    stores = []
    categories = []

    if not LOWES_MAP_PATH.exists():
        Actor.log.warning(f"LowesMap.txt not found at {LOWES_MAP_PATH}")
        return stores, categories

    with open(LOWES_MAP_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Store URLs: https://www.lowes.com/store/WA-Arlington/0061
            if '/store/' in line:
                match = re.search(r'/store/([A-Z]{2})-([^/]+)/(\d+)', line)
                if match:
                    state, city, store_id = match.groups()
                    stores.append({
                        "url": line,
                        "store_id": store_id,
                        "city": city.replace('-', ' '),
                        "state": state,
                        "name": f"{city.replace('-', ' ')}, {state} (#{store_id})"
                    })

            # Category URLs: https://www.lowes.com/pl/...
            elif '/pl/' in line and 'the-back-aisle' not in line.lower():
                # Extract category name from URL
                match = re.search(r'/pl/([^/]+)', line)
                if match:
                    cat_slug = match.group(1)
                    cat_name = cat_slug.split('-')[0].replace('-', ' ').title()
                    categories.append({
                        "url": line,
                        "name": cat_name
                    })

    Actor.log.info(f"Loaded {len(stores)} stores and {len(categories)} categories from LowesMap.txt")
    return stores, categories


# ============================================================================
# HUMAN BEHAVIOR SIMULATION
# ============================================================================

async def human_mouse_move(page: Page):
    """Human-like mouse movement with easing"""
    viewport = page.viewport_size
    width = viewport.get('width', 1440) if viewport else 1440
    height = viewport.get('height', 900) if viewport else 900

    start_x = random.random() * width * 0.3
    start_y = random.random() * height * 0.3
    end_x = width * 0.4 + random.random() * width * 0.4
    end_y = height * 0.4 + random.random() * height * 0.4

    steps = 10 + int(random.random() * 10)
    for i in range(steps + 1):
        progress = i / steps
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep((15 + random.random() * 25) / 1000)


async def human_scroll(page: Page):
    """Human-like scrolling"""
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((40 + random.random() * 80) / 1000)


async def warmup_session(page: Page):
    """CRITICAL: Warm up session with homepage visit and human behavior"""
    Actor.log.info("Warming up browser session...")

    await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)

    await human_mouse_move(page)
    await asyncio.sleep(1 + random.random())
    await human_scroll(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)
    await human_mouse_move(page)
    await asyncio.sleep(0.5 + random.random() * 0.5)

    Actor.log.info("Session warm-up complete")


async def set_store_context(page: Page, store_url: str, store_name: str):
    """Set store context by visiting store page and clicking 'Set Store'"""
    Actor.log.info(f"Setting store: {store_name}")

    await page.goto(store_url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(2)

    store_buttons = [
        "button:has-text('Set Store')",
        "button:has-text('Set as My Store')",
        "button:has-text('Make This My Store')",
    ]

    for selector in store_buttons:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click(timeout=8000)
                await asyncio.sleep(1.5)
                Actor.log.info(f"Store set: {store_name}")
                return True
        except:
            continue

    Actor.log.warning(f"Could not set store: {store_name}")
    return False


# ============================================================================
# SCRAPING FUNCTIONS
# ============================================================================

async def scrape_page(page: Page, url: str, category_name: str, store_info: dict, page_num: int = 1) -> list[dict]:
    """Scrape one page of products"""
    products = []

    # Add page number to URL if not first page
    page_url = url
    if page_num > 1:
        separator = '&' if '?' in url else '?'
        page_url = f"{url}{separator}offset={(page_num - 1) * PAGE_SIZE}"

    # Human behavior before navigation
    await asyncio.sleep(0.5 + random.random() * 0.5)

    # Navigate
    await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)

    # Human behavior after navigation
    await asyncio.sleep(1 + random.random())
    await human_mouse_move(page)
    await human_scroll(page)
    await asyncio.sleep(1)

    # Check if blocked
    title = await page.title()
    if "Access Denied" in title:
        Actor.log.error(f"BLOCKED on {category_name} page {page_num}")
        return []

    # Find product cards
    selectors_to_try = [
        '[class*="ProductCard"]',
        '[class*="product-card"]',
        'article',
        '[data-test="product-pod"]',
    ]

    product_cards = []
    for selector in selectors_to_try:
        cards = await page.locator(selector).all()
        if len(cards) > len(product_cards):
            product_cards = cards

    if not product_cards:
        Actor.log.info(f"{category_name} page {page_num}: No products found (end of results)")
        return []

    # Extract product data
    for card in product_cards:
        try:
            # Check for product link
            pd_links = await card.locator("a[href*='/pd/']").all()
            if not pd_links:
                continue

            href = await pd_links[0].get_attribute("href") or ""
            if not href:
                continue

            # Extract title
            title_text = (await pd_links[0].inner_text()).strip()
            if not title_text:
                title_selector = ":scope [data-testid='item-description'], :scope a[data-testid='item-description-link'], :scope h3, :scope h2"
                title_el = card.locator(title_selector).first
                if await title_el.count() > 0:
                    title_text = await title_el.inner_text()

            # Extract price
            price_text = ""
            price_selector = ":scope [data-testid='regular-price'], :scope [data-testid='current-price'], :scope [data-test*='price'], :scope [data-testid*='price']"
            price_el = card.locator(price_selector).first
            if await price_el.count() > 0:
                price_text = await price_el.inner_text()

            # Check for "was" price (indicates markdown)
            was_price = ""
            was_selector = ":scope [data-testid='was-price'], :scope [data-test*='was'], :scope [class*='was-price']"
            was_el = card.locator(was_selector).first
            if await was_el.count() > 0:
                was_price = await was_el.inner_text()

            if title_text and href and len(title_text) > 5:
                products.append({
                    "title": title_text.strip(),
                    "price": price_text.strip() if price_text else "N/A",
                    "was_price": was_price.strip() if was_price else "",
                    "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
                    "category": category_name,
                    "store_id": store_info["store_id"],
                    "store_name": store_info["name"],
                    "store_city": store_info["city"],
                    "store_state": store_info["state"],
                    "scraped_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            continue

    Actor.log.info(f"{store_info['name']} - {category_name} page {page_num}: {len(products)} products")
    return products


async def scrape_category_all_pages(page: Page, category: dict, store_info: dict, max_pages: int = 10) -> list[dict]:
    """Scrape all pages of a category"""
    all_products = []

    for page_num in range(1, max_pages + 1):
        products = await scrape_page(page, category["url"], category["name"], store_info, page_num)

        if not products:
            break  # No more products

        all_products.extend(products)

        # Stop if we got less than expected (last page)
        if len(products) < PAGE_SIZE * 0.5:
            break

    return all_products


async def scrape_store(store: dict, categories: list[dict], proxy_url: str = None):
    """Scrape all categories for one store"""
    Actor.log.info(f"Starting scraper for store: {store['name']}")

    async with async_playwright() as p:
        # Setup browser profile
        profile_dir = Path(f".playwright-profiles/store-{store['store_id']}")
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Browser launch args
        launch_args = {
            "headless": True,  # Run headless on Apify
            "channel": "chrome",
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
            ]
        }

        # Add proxy if provided
        if proxy_url:
            launch_args["proxy"] = {"server": proxy_url}
            Actor.log.info(f"Using proxy: {proxy_url}")

        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            **launch_args
        )

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Warmup and set store
            await warmup_session(page)
            await set_store_context(page, store["url"], store["name"])

            # Scrape all categories
            store_products = []
            for category in categories:
                products = await scrape_category_all_pages(page, category, store, max_pages=20)
                store_products.extend(products)

                # Push data incrementally
                if products:
                    await Actor.push_data(products)

                await asyncio.sleep(1)  # Small delay between categories

            Actor.log.info(f"Store {store['name']} complete: {len(store_products)} products")
            return store_products

        except Exception as e:
            Actor.log.error(f"Error scraping store {store['name']}: {e}")
            return []
        finally:
            await context.close()


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main():
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}

        # Configuration
        test_mode = actor_input.get("testMode", False)
        max_stores = actor_input.get("maxStores", 2 if test_mode else 999)
        max_categories = actor_input.get("maxCategories", 3 if test_mode else 999)
        proxy_url = actor_input.get("proxyUrl")  # Off-site residential proxy
        state_filter = actor_input.get("stateFilter", ["WA", "OR"])  # Which states to scrape

        Actor.log.info("=" * 70)
        Actor.log.info("Lowe's Full Catalog Scraper - WA/OR Stores")
        Actor.log.info("=" * 70)
        Actor.log.info(f"Test mode: {test_mode}")
        Actor.log.info(f"Max stores: {max_stores}")
        Actor.log.info(f"Max categories per store: {max_categories}")
        Actor.log.info(f"State filter: {state_filter}")
        if proxy_url:
            Actor.log.info(f"Using external proxy: {proxy_url}")

        # Load stores and categories
        all_stores, all_categories = load_stores_and_categories()

        # Filter stores by state
        if state_filter and state_filter != ["WA", "OR"]:
            all_stores = [s for s in all_stores if s["state"] in state_filter]
            Actor.log.info(f"Filtered to {len(all_stores)} stores in {state_filter}")

        # Apply limits
        stores = all_stores[:max_stores]
        categories = all_categories[:max_categories]

        Actor.log.info(f"Scraping {len(stores)} stores x {len(categories)} categories = {len(stores) * len(categories)} total scrapes")

        # Run stores in parallel batches
        total_products = 0
        for i in range(0, len(stores), MAX_CONCURRENT_STORES):
            batch = stores[i:i + MAX_CONCURRENT_STORES]
            Actor.log.info(f"\nStarting batch {i//MAX_CONCURRENT_STORES + 1}: {len(batch)} stores in parallel")

            tasks = [scrape_store(store, categories, proxy_url) for store in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    total_products += len(result)

        Actor.log.info("=" * 70)
        Actor.log.info(f"Scraping complete! Total products: {total_products}")
        Actor.log.info("=" * 70)
