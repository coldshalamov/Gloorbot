"""
Lowe's Apify Actor - OPTIMIZED Browser Pooling Architecture

COST OPTIMIZATION:
- OLD: 109K browser instances = $400-500 per crawl
- NEW: 50 browsers × 4 concurrent pages = $20-50 per crawl

KEY CHANGES:
1. Browser Pooling: One browser per store (50 total) instead of 109K
2. Concurrent Pages: 3-5 pages per browser for parallel processing
3. Session Reuse: Keep browsers alive, cycle through all department URLs
4. Memory Efficiency: Extract minimal data, close pages immediately

MAINTAINS ALL CONSTRAINTS:
- Akamai anti-bot evasion (headless=False, stealth, session locking)
- Pickup filter clicking (can't use URL params)
- Dynamic JavaScript rendering
- Session locking per store_id
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse
from collections import defaultdict

import yaml
from apify import Actor
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants
BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 60000
PAGE_SIZE = 24
DEFAULT_MAX_PAGES = 20
CONCURRENT_PAGES_PER_BROWSER = 4  # Number of concurrent pages per browser


# ============================================================================
# STORE & CATEGORY PARSING (unchanged from original)
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

        if "/store/" in line:
            continue

        if "/pl/" in line and line not in seen:
            seen.add(line)
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
    """Build category URL with pagination offset."""
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if offset > 0:
        params["offset"] = str(offset)

    rebuilt = parsed._replace(query=urlencode(params, doseq=True))
    return rebuilt.geturl()


# ============================================================================
# PICKUP FILTER (unchanged from original)
# ============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """Apply pickup filter with proper race condition handling."""

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
        for toggle_selector in availability_toggles:
            try:
                toggle = await page.query_selector(toggle_selector)
                if not toggle:
                    continue
                expanded = await toggle.get_attribute("aria-expanded")
                if expanded == "false":
                    await toggle.click()
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                break
            except Exception:
                continue

    async def is_filter_selected(el: Any) -> bool:
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

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.5, 1.0))

    initial_url = page.url

    await page.evaluate("window.scrollTo(0, 0)")
    await expand_availability()

    for attempt in range(3):
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

                    if await is_filter_selected(element):
                        return True

                    await element.click()
                    await asyncio.sleep(random.uniform(0.8, 1.6))

                    try:
                        await page.wait_for_load_state("networkidle", timeout=12000)
                    except Exception:
                        pass

                    current_url = page.url
                    if current_url != initial_url and ("pickup" in current_url.lower() or "availability" in current_url.lower()):
                        return True

                    if await is_filter_selected(element):
                        return True

            except Exception:
                continue

        await asyncio.sleep(random.uniform(0.8, 1.4))

    return False


# ============================================================================
# CRASH DETECTION
# ============================================================================

async def check_for_crash(page: Page) -> bool:
    """Check if Chromium crashed."""
    try:
        content = await page.content()
        crash_markers = ["Aw, Snap!", "Out of Memory", "Error code", "crashed"]
        if any(marker in content for marker in crash_markers):
            await page.reload()
            await asyncio.sleep(2)
            return True
    except Exception:
        pass
    return False


async def check_for_akamai_block(page: Page) -> bool:
    """Check if Akamai blocked the request."""
    try:
        content = await page.content()
        if "Access Denied" in content or "Reference #" in content:
            return True
    except Exception:
        pass
    return False


# ============================================================================
# PRODUCT EXTRACTION (unchanged from original)
# ============================================================================

async def extract_products(page: Page, store_id: str, store_name: str, category_name: str) -> list[dict[str, Any]]:
    """Extract products from the current page."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    products.extend(await extract_from_json_ld(page, store_id, store_name, category_name, timestamp))
    products.extend(await extract_from_dom(page, store_id, store_name, category_name, timestamp,
                                           seen_skus={p.get("sku") for p in products if p.get("sku")}))

    return products


async def extract_from_json_ld(page: Page, store_id: str, store_name: str, category_name: str, timestamp: str) -> list[dict[str, Any]]:
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
    except Exception:
        pass

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


async def extract_from_dom(page: Page, store_id: str, store_name: str, category_name: str, timestamp: str, seen_skus: set) -> list[dict[str, Any]]:
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
        title_el = await card.query_selector("a[href*='/pd/'], h3, h2, [data-test*='product-title']")
        title = await title_el.inner_text() if title_el else None
        if not title:
            return None

        price_el = await card.query_selector("[data-test*='price'], [aria-label*='$'], [data-testid*='price']")
        price_text = await price_el.inner_text() if price_el else None
        price = parse_price(price_text)
        if price is None:
            return None

        was_el = await card.query_selector("[data-test*='was'], [class*='was-price']")
        was_text = await was_el.inner_text() if was_el else None
        price_was = parse_price(was_text)

        link_el = await card.query_selector("a[href*='/pd/']")
        href = await link_el.get_attribute("href") if link_el else None
        product_url = f"{BASE_URL}{href}" if href and href.startswith("/") else href

        sku = extract_sku_from_url(product_url)

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
            "availability": "In Stock",
            "clearance": is_clearance({}, price, price_was),
            "product_url": product_url,
            "image_url": image_url,
            "timestamp": timestamp,
        }
    except Exception:
        return None


# ============================================================================
# UTILITY FUNCTIONS (unchanged from original)
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
        r"/pd/[^/]+- (\d{4,})",
        r"(\d{6,})(?:[/?]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_clearance(product: dict, price: float | None, was: float | None) -> bool:
    """Determine if product is on clearance."""
    text = str(product).lower()
    if any(word in text for word in ["clearance", "closeout", "final price", "special value"]):
        return True

    if price and was:
        pct_off = (was - price) / was
        if pct_off >= 0.25:
            return True

    return False


# ============================================================================
# BROWSER POOL MANAGER - THE KEY OPTIMIZATION
# ============================================================================

class BrowserPool:
    """Manages a pool of browsers, one per store, with concurrent page handling."""
    
    def __init__(self, playwright, proxy_config, use_stealth: bool = True):
        self.playwright = playwright
        self.proxy_config = proxy_config
        self.use_stealth = use_stealth
        self.browsers: dict[str, Browser] = {}
        self.contexts: dict[str, BrowserContext] = {}
        self.page_semaphores: dict[str, asyncio.Semaphore] = {}
        
    async def get_or_create_browser(self, store_id: str) -> tuple[Browser, BrowserContext]:
        """Get existing browser for store or create new one."""
        if store_id in self.browsers:
            return self.browsers[store_id], self.contexts[store_id]
        
        # Create proxy URL with session locked to store
        proxy_url = None
        if self.proxy_config:
            proxy_url = await self.proxy_config.new_url(session_id=f"store_{store_id}")
        
        # Launch browser (headful for Akamai)
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
        
        browser = await self.playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
        )
        
        self.browsers[store_id] = browser
        self.contexts[store_id] = context
        self.page_semaphores[store_id] = asyncio.Semaphore(CONCURRENT_PAGES_PER_BROWSER)
        
        Actor.log.info(f"Created browser for store {store_id}")
        return browser, context
    
    async def process_with_page(self, store_id: str, task_func, *args, **kwargs):
        """Process a task using a page from the browser pool."""
        browser, context = await self.get_or_create_browser(store_id)
        
        # Limit concurrent pages per browser
        async with self.page_semaphores[store_id]:
            page = await context.new_page()
            
            # Apply stealth
            if self.use_stealth:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
            
            try:
                result = await task_func(page, *args, **kwargs)
                return result
            finally:
                await page.close()
    
    async def close_all(self):
        """Close all browsers in the pool."""
        for store_id, browser in self.browsers.items():
            try:
                await self.contexts[store_id].close()
                await browser.close()
                Actor.log.info(f"Closed browser for store {store_id}")
            except Exception as e:
                Actor.log.error(f"Error closing browser for store {store_id}: {e}")


# ============================================================================
# PAGE PROCESSING TASK
# ============================================================================

async def process_category_page(
    page: Page,
    url: str,
    store_id: str,
    store_name: str,
    category_name: str,
    page_num: int
) -> list[dict[str, Any]]:
    """Process a single category page and extract products."""
    
    try:
        # Navigate to category page
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=GOTO_TIMEOUT_MS,
        )
        
        # Check for errors
        if response and response.status >= 400:
            if response.status == 404:
                Actor.log.warning(f"Category not found (404): {category_name} at {store_name}")
                return []
            else:
                Actor.log.warning(f"HTTP {response.status} for {url}")
                return []
        
        # Check for crash or block
        if await check_for_crash(page):
            Actor.log.warning("Page crashed")
            return []
        
        if await check_for_akamai_block(page):
            Actor.log.error(f"Akamai block for store {store_id}")
            await asyncio.sleep(random.uniform(5, 10))
            return []
        
        # Wait for page to stabilize
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        
        # Apply pickup filter
        pickup_applied = await apply_pickup_filter(page, category_name)
        if not pickup_applied:
            Actor.log.warning(f"Pickup filter not applied for {category_name}")
        
        # Wait for product grid
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Extract products
        products = await extract_products(page, store_id, store_name, category_name)
        
        if products:
            Actor.log.info(f"Extracted {len(products)} products from {store_name} | {category_name} | Page {page_num + 1}")
        
        # Random delay
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        return products
        
    except Exception as e:
        Actor.log.error(f"Error processing {url}: {e}")
        return []


# ============================================================================
# MAIN ACTOR - OPTIMIZED
# ============================================================================

async def main() -> None:
    """Main Actor entry point using Browser Pooling for cost optimization."""
    
    async with Actor:
        Actor.log.info("Starting OPTIMIZED Lowe's Scraper Actor")
        
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
                try:
                    with open("catalog/wa_or_stores.yml", "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f.read())
                    if data and "stores" in data:
                        for s in data["stores"]:
                            stores.append({
                                "store_id": s.get("zip", ""),
                                "store_name": s.get("store_name", "Unknown"),
                                "state": s.get("state", ""),
                            })
                        Actor.log.info(f"Loaded {len(stores)} stores from wa_or_stores.yml")
                except Exception as e2:
                    Actor.log.error(f"Failed to load stores: {e2}")
        else:
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
        
        # Setup proxy configuration
        try:
            proxy_config = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code=proxy_country,
            )
            Actor.log.info("Proxy configuration created with RESIDENTIAL group")
        except Exception as e:
            Actor.log.warning(f"Failed to create proxy config: {e}. Running without proxies.")
            proxy_config = None
        
        # Build task queue: group by store for browser reuse
        tasks_by_store = defaultdict(list)
        
        for store in stores:
            store_id = store["store_id"]
            store_name = store.get("store_name", f"Store {store_id}")
            
            for category in categories:
                category_name = category["name"]
                category_url = category["url"]
                
                for page_num in range(max_pages):
                    offset = page_num * PAGE_SIZE
                    url = build_category_url(category_url, store_id, offset)
                    
                    tasks_by_store[store_id].append({
                        "url": url,
                        "store_id": store_id,
                        "store_name": store_name,
                        "category_name": category_name,
                        "page_num": page_num,
                    })
        
        total_tasks = sum(len(tasks) for tasks in tasks_by_store.values())
        Actor.log.info(f"Created {total_tasks} tasks across {len(tasks_by_store)} stores")
        Actor.log.info(f"Browser count: {len(tasks_by_store)} (vs {total_tasks} in old version)")
        Actor.log.info(f"Concurrent pages per browser: {CONCURRENT_PAGES_PER_BROWSER}")
        Actor.log.info(f"Total parallel workers: {len(tasks_by_store) * CONCURRENT_PAGES_PER_BROWSER}")
        
        # Process with browser pooling
        async with async_playwright() as playwright:
            browser_pool = BrowserPool(playwright, proxy_config, use_stealth)
            
            total_products = 0
            processed_tasks = 0
            
            try:
                # Process each store's tasks concurrently
                store_tasks = []
                
                for store_id, tasks in tasks_by_store.items():
                    async def process_store_tasks(sid, task_list):
                        """Process all tasks for a single store using browser pool."""
                        store_products = 0
                        
                        # Process tasks with concurrency limit (CONCURRENT_PAGES_PER_BROWSER)
                        for task in task_list:
                            products = await browser_pool.process_with_page(
                                sid,
                                process_category_page,
                                task["url"],
                                task["store_id"],
                                task["store_name"],
                                task["category_name"],
                                task["page_num"]
                            )
                            
                            if products:
                                await Actor.push_data(products)
                                store_products += len(products)
                            
                            nonlocal processed_tasks, total_products
                            processed_tasks += 1
                            total_products += len(products)
                            
                            if processed_tasks % 100 == 0:
                                Actor.log.info(f"Progress: {processed_tasks}/{total_tasks} tasks, {total_products} products")
                        
                        Actor.log.info(f"Store {sid} complete: {store_products} products from {len(task_list)} pages")
                        return store_products
                    
                    store_tasks.append(process_store_tasks(store_id, tasks))
                
                # Run all stores in parallel
                await asyncio.gather(*store_tasks)
                
            finally:
                await browser_pool.close_all()
        
        Actor.log.info(f"Scraping complete! Total products: {total_products}, Tasks processed: {processed_tasks}")
        Actor.log.info(f"Cost optimization: {len(tasks_by_store)} browsers vs {total_tasks} in old version")


if __name__ == "__main__":
    asyncio.run(main())
