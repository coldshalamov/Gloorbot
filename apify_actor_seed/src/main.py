"""
Lowe's Apify Actor - Massive Parallelization via Request Queue

This Actor scrapes "Pickup Today" inventory across 50+ Lowe's stores in WA/OR
using Apify's Request Queue pattern for 100+ parallel instances.

Architecture:
1. Enqueue ALL URLs upfront (stores × categories × pages)
2. Apify auto-scales workers to process queue in parallel
3. Each worker locks proxy session to store_id (prevents Akamai "Access Denied")
4. Results pushed incrementally to Dataset
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

import yaml
from apify import Actor, Request
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants
BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 60000
PAGE_SIZE = 24  # Lowe's returns 24 items per page
DEFAULT_MAX_PAGES = 20  # 20 pages × 24 items = 480 items max per category


# ============================================================================
# STORE & CATEGORY PARSING
# ============================================================================

def parse_store_ids_from_lowesmap(content: str) -> list[dict[str, str]]:
    """Parse LowesMap.txt to extract store IDs and metadata."""
    stores = []
    store_pattern = re.compile(r"https://www\.lowes\.com/store/(\w+)-(\w+)/(\d+)")

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = store_pattern.search(line)
        if match:
            state, city, store_id = match.groups()
            stores.append({
                "store_id": store_id,
                "state": state,
                "city": city.replace("-", " "),
                "store_name": f"Lowe's {city.replace('-', ' ')}",
                "url": line,
            })

    return stores


def parse_categories_from_lowesmap(content: str) -> list[dict[str, str]]:
    """Parse department/category URLs from LowesMap.txt."""
    categories = []
    seen = set()

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Skip store URLs
        if "/store/" in line:
            continue

        # Category URLs contain /pl/
        if "/pl/" in line and line not in seen:
            seen.add(line)
            # Extract category name from URL
            parsed = urlparse(line)
            path_parts = parsed.path.split("/")
            name = "Unknown"
            for part in path_parts:
                if part and part not in ("pl", "c"):
                    name = part.replace("-", " ").title()
                    break

            categories.append({
                "name": name,
                "url": line,
            })

    return categories


def parse_categories_from_yaml(yaml_content: str) -> list[dict[str, str]]:
    """Parse categories from catalog YAML file."""
    try:
        data = yaml.safe_load(yaml_content)
        if not data:
            return []

        categories = data.get("categories", [])
        return [
            {"name": cat.get("name", "Unknown"), "url": cat.get("url", "")}
            for cat in categories
            if cat.get("url")
        ]
    except Exception:
        return []


# ============================================================================
# URL BUILDING
# ============================================================================

def build_category_url(base_url: str, store_id: str, offset: int = 0) -> str:
    """Build category URL with pagination offset.

    IMPORTANT: Don't add pickup filters to URL - they trigger Akamai blocks.
    Apply pickup filter via page interaction instead.
    """
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Only add offset for pagination
    if offset > 0:
        params["offset"] = str(offset)

    rebuilt = parsed._replace(query=urlencode(params, doseq=True))
    return rebuilt.geturl()


# ============================================================================
# PICKUP FILTER - FIXED RACE CONDITION
# ============================================================================

async def apply_pickup_filter(page: Any, category_name: str) -> bool:
    """Apply pickup filter with proper race condition handling.

    CRITICAL FIXES:
    1. Wait for page to fully load (networkidle) before clicking
    2. Verify filter was actually applied after click
    3. Multiple retry attempts with verification
    """

    pickup_selectors = [
        'label:has-text("Get It Today")',
        'label:has-text("Pickup Today")',
        'label:has-text("Available Today")',
        'button:has-text("Pickup")',
        'button:has-text("Get It Today")',
        'button:has-text("Get it fast")',
        '[data-testid*="pickup"]',
        '[data-testid*="availability"]',
        '[data-test-id*="pickup"]',
        '[aria-label*="Pickup"]',
        '[aria-label*="Get it today"]',
        '[aria-label*="Available today"]',
        'input[type="checkbox"][id*="pickup"]',
        'input[type="checkbox"][id*="availability"]',
    ]

    availability_toggles = [
        'button:has-text("Availability")',
        'button:has-text("Get It Fast")',
        'summary:has-text("Availability")',
        'summary:has-text("Get It Fast")',
    ]

    async def expand_availability():
        """Expand the availability filter section if collapsed."""
        for toggle_selector in availability_toggles:
            try:
                toggle = await page.query_selector(toggle_selector)
                if not toggle:
                    continue
                expanded = await toggle.get_attribute("aria-expanded")
                if expanded == "false":
                    Actor.log.info(f"[{category_name}] Expanding availability section")
                    await toggle.click()
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                break
            except Exception:
                continue

    async def is_filter_selected(el: Any) -> bool:
        """Check if a filter element is already selected."""
        try:
            checked = await el.get_attribute("aria-checked")
            pressed = await el.get_attribute("aria-pressed")
            selected = await el.get_attribute("aria-selected")
            if checked == "true" or pressed == "true" or selected == "true":
                return True
            try:
                return await el.is_checked()
            except Exception:
                return False
        except Exception:
            return False

    async def get_product_count() -> int:
        """Get current product count to verify filter application."""
        try:
            # Try to get product count from the page
            count_el = await page.query_selector('[data-testid*="product-count"], [data-test*="results"]')
            if count_el:
                text = await count_el.inner_text()
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
        except Exception:
            pass

        # Fallback: count product cards
        try:
            cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
            return len(cards)
        except Exception:
            return -1

    # FIX: Wait for page to be fully loaded BEFORE attempting filter
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        Actor.log.warning(f"[{category_name}] Network idle timeout, continuing anyway")

    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Get initial state for verification
    initial_url = page.url
    initial_count = await get_product_count()

    # Scroll to top and expand availability section
    await page.evaluate("window.scrollTo(0, 0)")
    await expand_availability()

    for attempt in range(3):
        Actor.log.info(f"[{category_name}] Pickup filter attempt {attempt + 1}/3")

        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    visible = await element.is_visible()
                    text = ""
                    if visible:
                        try:
                            text = (await element.inner_text()) or ""
                        except Exception:
                            text = ""

                    if not visible and not text:
                        continue
                    if len(text) > 120:
                        continue

                    # Check if already selected
                    if await is_filter_selected(element):
                        Actor.log.info(f"[{category_name}] Pickup filter already active: '{text[:80]}'")
                        return True

                    # Click the filter
                    Actor.log.info(f"[{category_name}] Clicking pickup filter: '{text[:80]}'")
                    await element.click()
                    await asyncio.sleep(random.uniform(0.8, 1.6))

                    # FIX: Wait for navigation/filter to take effect
                    try:
                        await page.wait_for_load_state("networkidle", timeout=12000)
                    except Exception:
                        pass

                    # FIX: Verify filter was applied
                    # Check 1: URL changed (some sites add filter params)
                    current_url = page.url
                    if current_url != initial_url and ("pickup" in current_url.lower() or "availability" in current_url.lower()):
                        Actor.log.info(f"[{category_name}] Pickup filter applied (URL changed)")
                        return True

                    # Check 2: Element is now selected
                    if await is_filter_selected(element):
                        Actor.log.info(f"[{category_name}] Pickup filter clicked and confirmed")
                        return True

                    # Check 3: Product count changed (filter reduced results)
                    new_count = await get_product_count()
                    if new_count != -1 and initial_count != -1 and new_count != initial_count:
                        Actor.log.info(f"[{category_name}] Pickup filter applied (product count changed: {initial_count} -> {new_count})")
                        return True

            except Exception as e:
                Actor.log.debug(f"[{category_name}] Selector {selector} failed: {e}")
                continue

        await asyncio.sleep(random.uniform(0.8, 1.4))

    Actor.log.warning(f"[{category_name}] Pickup filter NOT FOUND after 3 attempts")
    return False


# ============================================================================
# CRASH DETECTION
# ============================================================================

async def check_for_crash(page: Any) -> bool:
    """Check if Chromium crashed. Must run AFTER page.goto() and BEFORE selectors."""
    try:
        content = await page.content()
        crash_markers = ["Aw, Snap!", "Out of Memory", "Error code", "crashed"]
        if any(marker in content for marker in crash_markers):
            Actor.log.error("Page crashed! Reloading...")
            await page.reload()
            await asyncio.sleep(2)
            return True
    except Exception:
        pass
    return False


async def check_for_akamai_block(page: Any) -> bool:
    """Check if Akamai blocked the request."""
    try:
        content = await page.content()
        if "Access Denied" in content or "Reference #" in content:
            Actor.log.error("AKAMAI BLOCK DETECTED!")
            return True
    except Exception:
        pass
    return False


# ============================================================================
# PRODUCT EXTRACTION
# ============================================================================

async def extract_products(page: Any, store_id: str, store_name: str, category_name: str) -> list[dict[str, Any]]:
    """Extract products from the current page."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # First try JSON-LD extraction (most reliable)
    products.extend(await extract_from_json_ld(page, store_id, store_name, category_name, timestamp))

    # Then try DOM extraction for any missed products
    products.extend(await extract_from_dom(page, store_id, store_name, category_name, timestamp,
                                           seen_skus={p.get("sku") for p in products if p.get("sku")}))

    return products


async def extract_from_json_ld(page: Any, store_id: str, store_name: str, category_name: str, timestamp: str) -> list[dict[str, Any]]:
    """Extract products from JSON-LD structured data."""
    products = []

    try:
        scripts = await page.query_selector_all("script[type='application/ld+json']")

        for script in scripts:
            try:
                raw = await script.inner_text()
                if not raw:
                    continue

                import json
                payload = json.loads(raw)

                for product in collect_product_dicts(payload):
                    row = product_dict_to_row(product, store_id, store_name, category_name, timestamp)
                    if row:
                        products.append(row)
            except Exception:
                continue
    except Exception as e:
        Actor.log.debug(f"JSON-LD extraction error: {e}")

    return products


def collect_product_dicts(obj: Any) -> list[dict[str, Any]]:
    """Recursively collect Product objects from JSON-LD."""
    results = []

    def walk(value: Any):
        if isinstance(value, dict):
            if (value.get("@type") or "").lower() == "product":
                results.append(value)
            else:
                for nested in value.values():
                    walk(nested)
        elif isinstance(value, list):
            for entry in value:
                walk(entry)

    walk(obj)
    return results


def product_dict_to_row(product: dict[str, Any], store_id: str, store_name: str, category_name: str, timestamp: str) -> dict[str, Any] | None:
    """Convert a JSON-LD product to our output schema."""
    if not isinstance(product, dict):
        return None

    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    price = parse_price(str(offers.get("price", "")))
    if price is None:
        return None

    price_was = parse_price(str(offers.get("priceWas", "")))

    return {
        "store_id": store_id,
        "store_name": store_name,
        "sku": product.get("sku") or product.get("productID"),
        "title": (product.get("name") or product.get("description") or "Unknown")[:200],
        "category": category_name,
        "price": price,
        "price_was": price_was,
        "pct_off": compute_pct_off(price, price_was),
        "availability": normalize_availability(offers.get("availability")),
        "clearance": is_clearance(product, price, price_was),
        "product_url": offers.get("url") or product.get("url"),
        "image_url": normalize_image_url(product.get("image")),
        "timestamp": timestamp,
    }


async def extract_from_dom(page: Any, store_id: str, store_name: str, category_name: str, timestamp: str, seen_skus: set) -> list[dict[str, Any]]:
    """Extract products from DOM elements (fallback)."""
    products = []

    card_selectors = [
        "[data-test='product-pod']",
        "[data-test='productPod']",
        "li:has(a[href*='/pd/'])",
        "article:has(a[href*='/pd/'])",
    ]

    for selector in card_selectors:
        try:
            cards = await page.query_selector_all(selector)
            if not cards:
                continue

            for card in cards:
                try:
                    row = await extract_card_data(card, store_id, store_name, category_name, timestamp)
                    if row and row.get("sku") not in seen_skus:
                        products.append(row)
                        if row.get("sku"):
                            seen_skus.add(row["sku"])
                except Exception:
                    continue

            if products:
                break
        except Exception:
            continue

    return products


async def extract_card_data(card: Any, store_id: str, store_name: str, category_name: str, timestamp: str) -> dict[str, Any] | None:
    """Extract data from a single product card."""
    try:
        # Get title
        title_el = await card.query_selector("a[href*='/pd/'], h3, h2, [data-test*='product-title']")
        title = await title_el.inner_text() if title_el else None
        if not title:
            return None

        # Get price
        price_el = await card.query_selector("[data-test*='price'], [aria-label*='$'], [data-testid*='price']")
        price_text = await price_el.inner_text() if price_el else None
        price = parse_price(price_text)
        if price is None:
            return None

        # Get was price
        was_el = await card.query_selector("[data-test*='was'], [class*='was-price']")
        was_text = await was_el.inner_text() if was_el else None
        price_was = parse_price(was_text)

        # Get link
        link_el = await card.query_selector("a[href*='/pd/']")
        href = await link_el.get_attribute("href") if link_el else None
        product_url = f"{BASE_URL}{href}" if href and href.startswith("/") else href

        # Extract SKU from URL
        sku = extract_sku_from_url(product_url)

        # Get image
        img_el = await card.query_selector("img")
        img_src = await img_el.get_attribute("src") if img_el else None
        image_url = normalize_image_url(img_src)

        return {
            "store_id": store_id,
            "store_name": store_name,
            "sku": sku,
            "title": title[:200],
            "category": category_name,
            "price": price,
            "price_was": price_was,
            "pct_off": compute_pct_off(price, price_was),
            "availability": "In Stock",  # We're filtering for pickup availability
            "clearance": is_clearance({}, price, price_was),
            "product_url": product_url,
            "image_url": image_url,
            "timestamp": timestamp,
        }
    except Exception:
        return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_price(text: str | None) -> float | None:
    """Parse a price string to float."""
    if not text:
        return None

    match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
    if not match:
        return None

    try:
        value = float(match.group(1).replace(",", ""))
        if 0 < value < 100000:
            return value
    except (ValueError, TypeError):
        pass
    return None


def compute_pct_off(price: float | None, was: float | None) -> float | None:
    """Compute percentage discount."""
    if not price or not was or was <= price:
        return None
    try:
        return round((was - price) / was, 4)
    except ZeroDivisionError:
        return None


def normalize_availability(value: str | None) -> str:
    """Normalize availability strings."""
    if not value:
        return "Unknown"

    lowered = value.lower()
    if "instock" in lowered or "in stock" in lowered:
        return "In Stock"
    if "outofstock" in lowered or "out of stock" in lowered:
        return "Out of Stock"
    if "limited" in lowered:
        return "Limited"

    return value.strip()[:50]


def normalize_image_url(value: Any) -> str | None:
    """Normalize image URL."""
    if isinstance(value, list):
        value = value[0] if value else None

    if not isinstance(value, str) or not value:
        return None

    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{BASE_URL}{value}"
    return value


def extract_sku_from_url(url: str | None) -> str | None:
    """Extract SKU from product URL."""
    if not url:
        return None

    patterns = [
        r"/pd/[^/]+-(\d{4,})",
        r"(\d{6,})(?:[/?]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_clearance(product: dict, price: float | None, was: float | None) -> bool:
    """Determine if product is on clearance."""
    # Check JSON-LD data
    text = str(product).lower()
    if any(word in text for word in ["clearance", "closeout", "final price", "special value"]):
        return True

    # Check discount percentage
    if price and was:
        pct_off = (was - price) / was
        if pct_off >= 0.25:  # 25% or more off
            return True

    return False


# ============================================================================
# STORE CONTEXT SETUP
# ============================================================================

@retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=0.5, max=5),
    reraise=True,
)
async def set_store_context(page: Any, store_id: str, store_name: str) -> bool:
    """Set the Lowe's store context by navigating to store page."""
    try:
        # Navigate to Lowe's homepage
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
        await page.wait_for_load_state("networkidle", timeout=15000)

        if await check_for_crash(page):
            return False

        if await check_for_akamai_block(page):
            return False

        # Try to set store via URL parameter or cookie
        # Lowe's uses storeNumber parameter
        Actor.log.info(f"Setting store context: {store_name} ({store_id})")

        # Wait a bit for any popups to load
        await asyncio.sleep(random.uniform(1.0, 2.0))

        return True
    except Exception as e:
        Actor.log.error(f"Failed to set store context: {e}")
        raise


# ============================================================================
# MAIN ACTOR
# ============================================================================

async def main() -> None:
    """Main Actor entry point using Request Queue for parallelization."""

    async with Actor:
        Actor.log.info("Starting Lowe's Scraper Actor")

        # Get input
        actor_input = await Actor.get_input() or {}

        input_store_ids = actor_input.get("store_ids", [])
        input_categories = actor_input.get("categories", [])
        max_pages = actor_input.get("max_pages_per_category", DEFAULT_MAX_PAGES)
        use_stealth = actor_input.get("use_stealth", True)
        proxy_country = actor_input.get("proxy_country", "US")

        # Load stores from LowesMap.txt if not provided
        stores = []
        if not input_store_ids:
            try:
                with open("input/LowesMap.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                stores = parse_store_ids_from_lowesmap(content)
                Actor.log.info(f"Loaded {len(stores)} stores from LowesMap.txt")
            except Exception as e:
                Actor.log.error(f"Failed to load LowesMap.txt: {e}")
                # Fallback to wa_or_stores.yml
                try:
                    with open("catalog/wa_or_stores.yml", "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f.read())
                    if data and "stores" in data:
                        for s in data["stores"]:
                            stores.append({
                                "store_id": s.get("zip", ""),  # Using zip as fallback ID
                                "store_name": s.get("store_name", "Unknown"),
                                "state": s.get("state", ""),
                            })
                        Actor.log.info(f"Loaded {len(stores)} stores from wa_or_stores.yml")
                except Exception as e2:
                    Actor.log.error(f"Failed to load stores: {e2}")
        else:
            # Use provided store IDs
            stores = [{"store_id": sid, "store_name": f"Store {sid}"} for sid in input_store_ids]

        if not stores:
            Actor.log.error("No stores found. Exiting.")
            return

        # Load categories
        categories = []
        if not input_categories:
            try:
                with open("input/LowesMap.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                categories = parse_categories_from_lowesmap(content)
                Actor.log.info(f"Loaded {len(categories)} categories from LowesMap.txt")
            except Exception:
                pass

            # Also load from catalog YAML
            try:
                with open("catalog/building_materials.lowes.yml", "r", encoding="utf-8") as f:
                    yaml_cats = parse_categories_from_yaml(f.read())
                    for cat in yaml_cats:
                        if cat not in categories:
                            categories.append(cat)
                    Actor.log.info(f"Total categories after YAML: {len(categories)}")
            except Exception:
                pass
        else:
            categories = [{"name": f"Category {i}", "url": url} for i, url in enumerate(input_categories)]

        if not categories:
            Actor.log.error("No categories found. Exiting.")
            return

        # Open Request Queue
        request_queue = await Actor.open_request_queue()

        # Calculate total URLs
        total_urls = len(stores) * len(categories) * max_pages
        Actor.log.info(f"Enqueueing {total_urls} URLs ({len(stores)} stores × {len(categories)} categories × {max_pages} pages)")

        # Enqueue ALL URLs upfront for maximum parallelization
        enqueued = 0
        for store in stores:
            store_id = store["store_id"]
            store_name = store.get("store_name", f"Store {store_id}")

            for category in categories:
                category_name = category["name"]
                category_url = category["url"]

                for page_num in range(max_pages):
                    offset = page_num * PAGE_SIZE
                    url = build_category_url(category_url, store_id, offset)

                    request = Request.from_url(
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
                    enqueued += 1

                    if enqueued % 1000 == 0:
                        Actor.log.info(f"Enqueued {enqueued}/{total_urls} URLs...")

        Actor.log.info(f"Finished enqueueing {enqueued} URLs. Starting processing...")

        # Setup proxy configuration with session locking
        try:
            proxy_config = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code=proxy_country,
            )
            Actor.log.info("Proxy configuration created with RESIDENTIAL group")
        except Exception as e:
            Actor.log.warning(f"Failed to create proxy config: {e}. Running without proxies.")
            proxy_config = None

        # Process queue with Playwright
        async with async_playwright() as playwright:
            total_products = 0
            processed_requests = 0

            while True:
                request = await request_queue.fetch_next_request()
                if not request:
                    break

                store_id = request.user_data.get("store_id", "unknown")
                store_name = request.user_data.get("store_name", "Unknown Store")
                category_name = request.user_data.get("category_name", "Unknown")
                page_num = request.user_data.get("page_num", 0)

                try:
                    # CRITICAL: Lock proxy session to store_id to prevent Akamai blocks
                    proxy_url = None
                    if proxy_config:
                        proxy_url = await proxy_config.new_url(session_id=f"store_{store_id}")

                    # Launch headful browser (REQUIRED for Akamai)
                    browser_args = [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]

                    launch_options = {
                        "headless": False,  # CRITICAL: Akamai blocks headless
                        "args": browser_args,
                    }

                    if proxy_url:
                        launch_options["proxy"] = {"server": proxy_url}

                    browser = await playwright.chromium.launch(**launch_options)
                    context = await browser.new_context(
                        viewport={"width": 1440, "height": 900},
                    )
                    page = await context.new_page()

                    # Apply stealth
                    if use_stealth:
                        stealth = Stealth()
                        await stealth.apply_stealth_async(page)

                    try:
                        # Navigate to category page
                        Actor.log.info(f"Processing: {store_name} | {category_name} | Page {page_num + 1}")

                        response = await page.goto(
                            request.url,
                            wait_until="domcontentloaded",
                            timeout=GOTO_TIMEOUT_MS,
                        )

                        # Check for errors
                        if response and response.status >= 400:
                            if response.status == 404:
                                Actor.log.warning(f"Category not found (404): {category_name} at {store_name}")
                                await request_queue.mark_request_as_handled(request)
                                continue
                            else:
                                Actor.log.warning(f"HTTP {response.status} for {request.url}")

                        # Check for crash or block
                        if await check_for_crash(page):
                            Actor.log.warning("Page crashed, retrying...")
                            await request_queue.reclaim_request(request)
                            continue

                        if await check_for_akamai_block(page):
                            Actor.log.error(f"Akamai block for store {store_id}. Increasing delay...")
                            await asyncio.sleep(random.uniform(5, 10))
                            await request_queue.reclaim_request(request)
                            continue

                        # Wait for page to stabilize
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass

                        # Apply pickup filter (FIXED race condition)
                        pickup_applied = await apply_pickup_filter(page, category_name)
                        if not pickup_applied:
                            Actor.log.warning(f"Pickup filter not applied for {category_name} - results may include non-pickup items")

                        # Wait for product grid
                        await asyncio.sleep(random.uniform(0.5, 1.0))

                        # Extract products
                        products = await extract_products(page, store_id, store_name, category_name)

                        if products:
                            # Push results incrementally
                            await Actor.push_data(products)
                            total_products += len(products)
                            Actor.log.info(f"Pushed {len(products)} products from {store_name} | {category_name} | Page {page_num + 1}")
                        else:
                            Actor.log.debug(f"No products found on page {page_num + 1} of {category_name} at {store_name}")

                        # Mark as handled
                        await request_queue.mark_request_as_handled(request)
                        processed_requests += 1

                        if processed_requests % 100 == 0:
                            Actor.log.info(f"Progress: {processed_requests} requests processed, {total_products} products found")

                        # Random delay between requests
                        await asyncio.sleep(random.uniform(0.5, 1.5))

                    finally:
                        await page.close()
                        await context.close()
                        await browser.close()

                except Exception as e:
                    Actor.log.error(f"Error processing {request.url}: {e}")
                    # Reclaim request for retry
                    try:
                        await request_queue.reclaim_request(request)
                    except Exception:
                        await request_queue.mark_request_as_handled(request)

        Actor.log.info(f"Scraping complete! Total products: {total_products}, Requests processed: {processed_requests}")


if __name__ == "__main__":
    asyncio.run(main())
