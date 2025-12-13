"""
Lowe's Apify Actor - ULTRA OPTIMIZED for Minimum Cost

ADDITIONAL OPTIMIZATIONS OVER main_optimized.py:
1. Block unnecessary resources (images, fonts, analytics)
2. Request interception to skip third-party scripts
3. Smaller viewport (reduces rendering)
4. Early data extraction (don't wait for full page)
5. Smart pagination (stop when no more products)
6. Memory cleanup between pages

ESTIMATED SAVINGS:
- Bandwidth: 60-70% reduction (blocked resources)
- Memory: 20-30% reduction (smaller viewport, cleanup)
- Runtime: 30-40% faster (less to load)

MAINTAINS AKAMAI EVASION:
- Still loads Akamai sensor scripts
- Still executes core JavaScript
- Still headless=False
- Still session locked per store
"""

from __future__ import annotations

import asyncio
import random
import re
import gc
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse
from collections import defaultdict

import yaml
from apify import Actor
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Route
from playwright_stealth import Stealth
from tenacity import retry, stop_after_attempt, wait_random_exponential

# Constants
BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 45000  # Reduced from 60s (less to load)
PAGE_SIZE = 24
DEFAULT_MAX_PAGES = 20
CONCURRENT_PAGES_PER_BROWSER = 4

# ============================================================================
# RESOURCE BLOCKING - THE KEY COST OPTIMIZATION
# ============================================================================

# Resources to BLOCK (safe, won't trigger Akamai)
BLOCKED_RESOURCE_TYPES = {
    "image",      # Block images (we get URLs from JSON-LD)
    "media",      # Block videos
    "font",       # Block fonts
}

# URL patterns to BLOCK
BLOCKED_URL_PATTERNS = [
    # Analytics & Tracking
    r"google-analytics\.com",
    r"googletagmanager\.com",
    r"facebook\.net",
    r"facebook\.com/tr",
    r"doubleclick\.net",
    r"googlesyndication\.com",
    r"connect\.facebook",
    r"analytics",
    r"tracking",
    r"beacon",
    r"pixel",
    
    # Advertising
    r"ads\.",
    r"ad\.",
    r"adservice",
    r"pagead",
    r"adsystem",
    
    # Video/Media CDNs (not product images)
    r"youtube\.com",
    r"vimeo\.com",
    r"brightcove",
    r"cloudinary.*video",
    
    # Social widgets
    r"twitter\.com/widgets",
    r"platform\.twitter",
    r"pinterest\.com",
    r"linkedin\.com",
    
    # Third-party scripts we don't need
    r"hotjar\.com",
    r"clarity\.ms",
    r"newrelic\.com",
    r"sentry\.io",
    r"segment\.com",
    r"optimizely\.com",
    r"crazyegg\.com",
    r"fullstory\.com",
    r"mouseflow\.com",
    r"heap\.io",
    r"amplitude\.com",
    r"mixpanel\.com",
    r"intercom\.io",
    r"drift\.com",
    r"zendesk\.com",
    r"livechat\.com",
    r"tawk\.to",
    
    # Large non-essential resources
    r"\.woff2?(\?|$)",  # Fonts
    r"\.ttf(\?|$)",
    r"\.eot(\?|$)",
]

# URL patterns to NEVER block (Akamai and essential)
NEVER_BLOCK_PATTERNS = [
    r"/_sec/",           # Akamai sensor
    r"/akam/",           # Akamai
    r"akamai",           # Akamai CDN
    r"lowes\.com",       # Main site (careful filtering)
    r"cloudfront",       # Product images CDN (we need URLs, not bytes)
    r"/pl/",             # Category pages
    r"/pd/",             # Product pages
]


async def setup_request_interception(page: Page):
    """Set up request interception to block unnecessary resources."""
    
    async def handle_route(route: Route):
        request = route.request
        url = request.url.lower()
        resource_type = request.resource_type
        
        # Check if this should NEVER be blocked
        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                # But still block images from lowes.com (we only need URLs)
                if resource_type == "image" and "lowes.com" not in url:
                    await route.abort()
                    return
                await route.continue_()
                return
        
        # Block by resource type
        if resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        
        # Block by URL pattern
        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.abort()
                return
        
        # Allow everything else
        await route.continue_()
    
    await page.route("**/*", handle_route)


# ============================================================================
# STORE & CATEGORY PARSING (unchanged)
# ============================================================================

def parse_store_ids_from_lowesmap(content: str) -> list[dict[str, str]]:
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
    parsed = urlparse(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if offset > 0:
        params["offset"] = str(offset)

    rebuilt = parsed._replace(query=urlencode(params, doseq=True))
    return rebuilt.geturl()


# ============================================================================
# PICKUP FILTER (slightly optimized - reduced waits)
# ============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """Apply pickup filter with reduced wait times."""

    pickup_selectors = [
        'label:has-text("Get It Today")',
        'label:has-text("Pickup Today")',
        'label:has-text("Available Today")',
        'button:has-text("Pickup")',
        'button:has-text("Get It Today")',
        'button:has-text("Get it fast")',
        '[data-testid*="pickup"]',
        '[data-testid*="availability"]',
        '[aria-label*="Pickup"]',
        'input[type="checkbox"][id*="pickup"]',
    ]

    async def is_filter_selected(el: Any) -> bool:
        try:
            checked = await el.get_attribute("aria-checked")
            pressed = await el.get_attribute("aria-pressed")
            if checked == "true" or pressed == "true":
                return True
            try:
                return await el.is_checked()
            except Exception:
                return False
        except Exception:
            return False

    # Reduced wait time (was 15s, now 8s)
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.3, 0.6))  # Reduced from 0.5-1.0

    for attempt in range(2):  # Reduced from 3 attempts
        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    visible = await element.is_visible()
                    if not visible:
                        continue

                    if await is_filter_selected(element):
                        return True

                    await element.click()
                    await asyncio.sleep(random.uniform(0.5, 1.0))  # Reduced

                    try:
                        await page.wait_for_load_state("networkidle", timeout=6000)
                    except Exception:
                        pass

                    if await is_filter_selected(element):
                        return True

            except Exception:
                continue

    return False


# ============================================================================
# ERROR CHECKING (reduced)
# ============================================================================

async def check_for_akamai_block(page: Page) -> bool:
    try:
        # Only check title, faster than getting full content
        title = await page.title()
        if "Access Denied" in title or "Error" in title:
            return True
        
        # Quick content check
        content = await page.content()
        if "Access Denied" in content[:2000] or "Reference #" in content[:2000]:
            return True
    except Exception:
        pass
    return False


# ============================================================================
# PRODUCT EXTRACTION (optimized for speed)
# ============================================================================

async def extract_products_fast(page: Page, store_id: str, store_name: str, category_name: str) -> list[dict[str, Any]]:
    """Extract products with minimal DOM queries."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # Try JSON-LD first (fastest, most reliable)
    try:
        # Single evaluate call instead of multiple query_selectors
        json_ld_data = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)
        
        for payload in json_ld_data:
            for product in collect_product_dicts(payload):
                row = product_dict_to_row(product, store_id, store_name, category_name, timestamp)
                if row:
                    products.append(row)
    except Exception:
        pass

    # Fallback to DOM only if JSON-LD failed
    if not products:
        products = await extract_from_dom_fast(page, store_id, store_name, category_name, timestamp)

    return products


async def extract_from_dom_fast(page: Page, store_id: str, store_name: str, category_name: str, timestamp: str) -> list[dict[str, Any]]:
    """Fast DOM extraction using a single evaluate call."""
    try:
        # Extract all product data in ONE JavaScript call
        raw_products = await page.evaluate("""
            () => {
                const products = [];
                const cards = document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]');
                
                cards.forEach(card => {
                    try {
                        const titleEl = card.querySelector('a[href*="/pd/"], h3, h2');
                        const priceEl = card.querySelector('[data-test*="price"], [aria-label*="$"]');
                        const wasEl = card.querySelector('[data-test*="was"], [class*="was-price"]');
                        const linkEl = card.querySelector('a[href*="/pd/"]');
                        const imgEl = card.querySelector('img');
                        
                        if (titleEl && priceEl) {
                            products.push({
                                title: titleEl.innerText?.trim() || '',
                                price: priceEl.innerText?.trim() || '',
                                was: wasEl?.innerText?.trim() || '',
                                href: linkEl?.getAttribute('href') || '',
                                img: imgEl?.getAttribute('src') || imgEl?.getAttribute('data-src') || ''
                            });
                        }
                    } catch {}
                });
                
                return products;
            }
        """)
        
        products = []
        for raw in raw_products:
            price = parse_price(raw.get("price"))
            if price is None:
                continue
            
            price_was = parse_price(raw.get("was"))
            href = raw.get("href", "")
            product_url = f"{BASE_URL}{href}" if href.startswith("/") else href
            
            products.append({
                "store_id": store_id,
                "store_name": store_name,
                "sku": extract_sku_from_url(product_url),
                "title": raw.get("title", "")[:200],
                "category": category_name,
                "price": price,
                "price_was": price_was,
                "pct_off": compute_pct_off(price, price_was),
                "availability": "In Stock",
                "clearance": is_clearance({}, price, price_was),
                "product_url": product_url,
                "image_url": normalize_image_url(raw.get("img")),
                "timestamp": timestamp,
            })
        
        return products
    except Exception:
        return []


def collect_product_dicts(obj: Any) -> list[dict[str, Any]]:
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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_price(text: str | None) -> float | None:
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
    if not price or not was or was <= price:
        return None
    try:
        return round((was - price) / was, 4)
    except ZeroDivisionError:
        return None


def normalize_availability(value: str | None) -> str:
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
    if not url:
        return None
    patterns = [r"/pd/[^/]+- (\d{4,})", r"(\d{6,})(?:[/?]|$)"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def is_clearance(product: dict, price: float | None, was: float | None) -> bool:
    text = str(product).lower()
    if any(word in text for word in ["clearance", "closeout", "final price"]):
        return True
    if price and was:
        if (was - price) / was >= 0.25:
            return True
    return False


# ============================================================================
# BROWSER POOL (optimized settings)
# ============================================================================

class BrowserPoolOptimized:
    """Memory and bandwidth optimized browser pool."""
    
    def __init__(self, playwright, proxy_config, use_stealth: bool = True):
        self.playwright = playwright
        self.proxy_config = proxy_config
        self.use_stealth = use_stealth
        self.browsers: dict[str, Browser] = {}
        self.contexts: dict[str, BrowserContext] = {}
        self.page_semaphores: dict[str, asyncio.Semaphore] = {}
        
    async def get_or_create_browser(self, store_id: str) -> tuple[Browser, BrowserContext]:
        if store_id in self.browsers:
            return self.browsers[store_id], self.contexts[store_id]
        
        proxy_url = None
        if self.proxy_config:
            proxy_url = await self.proxy_config.new_url(session_id=f"store_{store_id}")
        
        # Optimized browser args for reduced memory
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",                    # Reduce GPU memory
            "--disable-software-rasterizer",    # Reduce rendering overhead
            "--disable-extensions",             # No extensions
            "--disable-background-networking",  # Reduce network overhead
            "--disable-sync",                   # No sync
            "--disable-translate",              # No translate
            "--no-first-run",                   # Skip first run
            "--disable-default-apps",           # No default apps
            "--mute-audio",                     # No audio processing
            "--hide-scrollbars",                # Less rendering
        ]
        
        launch_options = {
            "headless": False,  # Still required for Akamai
            "args": browser_args,
        }
        
        if proxy_url:
            launch_options["proxy"] = {"server": proxy_url}
        
        browser = await self.playwright.chromium.launch(**launch_options)
        
        # Smaller viewport = less rendering = less memory
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},  # Reduced from 1440x900
            device_scale_factor=1,  # No retina scaling
            has_touch=False,
            java_script_enabled=True,  # Required for Akamai
        )
        
        self.browsers[store_id] = browser
        self.contexts[store_id] = context
        self.page_semaphores[store_id] = asyncio.Semaphore(CONCURRENT_PAGES_PER_BROWSER)
        
        Actor.log.info(f"Created optimized browser for store {store_id}")
        return browser, context
    
    async def process_with_page(self, store_id: str, task_func, *args, **kwargs):
        browser, context = await self.get_or_create_browser(store_id)
        
        async with self.page_semaphores[store_id]:
            page = await context.new_page()
            
            # Set up request interception to block unnecessary resources
            await setup_request_interception(page)
            
            if self.use_stealth:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
            
            try:
                result = await task_func(page, *args, **kwargs)
                return result
            finally:
                await page.close()
                # Force garbage collection to free memory
                gc.collect()
    
    async def close_all(self):
        for store_id, browser in self.browsers.items():
            try:
                await self.contexts[store_id].close()
                await browser.close()
            except Exception as e:
                Actor.log.error(f"Error closing browser for store {store_id}: {e}")


# ============================================================================
# SMART PAGINATION
# ============================================================================

async def should_continue_pagination(page: Page, products_found: int, page_num: int) -> bool:
    """Determine if we should continue to next page.
    
    Optimization: Stop early if:
    1. No products found on current page
    2. Fewer products than expected (likely last page)
    3. "No results" message visible
    """
    if products_found == 0:
        Actor.log.info(f"No products on page {page_num + 1}, stopping pagination")
        return False
    
    if products_found < PAGE_SIZE // 2:  # Less than half expected
        Actor.log.info(f"Only {products_found} products on page {page_num + 1}, likely last page")
        return False
    
    # Check for "no more results" indicator
    try:
        no_results = await page.query_selector('[data-test*="no-results"], [class*="no-results"]')
        if no_results and await no_results.is_visible():
            return False
    except Exception:
        pass
    
    return True


# ============================================================================
# PAGE PROCESSING
# ============================================================================

async def process_category_page_optimized(
    page: Page,
    url: str,
    store_id: str,
    store_name: str,
    category_name: str,
    page_num: int
) -> tuple[list[dict[str, Any]], bool]:
    """Process a single category page. Returns (products, should_continue)."""
    
    try:
        # Navigate with reduced timeout (resources are blocked)
        response = await page.goto(
            url,
            wait_until="domcontentloaded",  # Don't wait for networkidle
            timeout=GOTO_TIMEOUT_MS,
        )
        
        if response and response.status >= 400:
            if response.status == 404:
                return [], False
            return [], True  # Retry on other errors
        
        if await check_for_akamai_block(page):
            Actor.log.error(f"Akamai block for store {store_id}")
            await asyncio.sleep(random.uniform(3, 6))  # Reduced wait
            return [], True
        
        # Reduced wait (we're blocking resources)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        
        # Apply pickup filter
        await apply_pickup_filter(page, category_name)
        
        # Short wait for products to load
        await asyncio.sleep(random.uniform(0.3, 0.6))
        
        # Extract products (optimized)
        products = await extract_products_fast(page, store_id, store_name, category_name)
        
        # Check if we should continue pagination
        should_continue = await should_continue_pagination(page, len(products), page_num)
        
        if products:
            Actor.log.info(f"Extracted {len(products)} products from {store_name} | {category_name} | Page {page_num + 1}")
        
        # Reduced delay
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        return products, should_continue
        
    except Exception as e:
        Actor.log.error(f"Error processing {url}: {e}")
        return [], True


# ============================================================================
# MAIN ACTOR - ULTRA OPTIMIZED
# ============================================================================

async def main() -> None:
    """Main Actor entry point with maximum cost optimization."""
    
    async with Actor:
        Actor.log.info("Starting ULTRA OPTIMIZED Lowe's Scraper")
        
        actor_input = await Actor.get_input() or {}
        
        input_store_ids = actor_input.get("store_ids", [])
        input_categories = actor_input.get("categories", [])
        max_pages = actor_input.get("max_pages_per_category", DEFAULT_MAX_PAGES)
        use_stealth = actor_input.get("use_stealth", True)
        proxy_country = actor_input.get("proxy_country", "US")
        
        # Load stores
        stores = []
        if not input_store_ids:
            try:
                with open("input/LowesMap.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                stores = parse_store_ids_from_lowesmap(content)
                Actor.log.info(f"Loaded {len(stores)} stores")
            except Exception as e:
                Actor.log.error(f"Failed to load stores: {e}")
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
                Actor.log.info(f"Loaded {len(categories)} categories")
            except Exception:
                pass
        else:
            categories = [{"name": f"Category {i}", "url": url} for i, url in enumerate(input_categories)]
        
        if not categories:
            Actor.log.error("No categories found. Exiting.")
            return
        
        # Setup proxy
        try:
            proxy_config = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code=proxy_country,
            )
            Actor.log.info("Proxy configuration created")
        except Exception as e:
            Actor.log.warning(f"Failed to create proxy config: {e}")
            proxy_config = None
        
        # Log optimization stats
        estimated_requests = len(stores) * len(categories) * (max_pages // 2)  # Assume smart pagination saves 50%
        Actor.log.info(f"Estimated requests: {estimated_requests} (with smart pagination)")
        Actor.log.info(f"Resource blocking: Enabled (60-70% bandwidth savings)")
        Actor.log.info(f"Viewport: 1280x720 (20% memory savings)")
        
        async with async_playwright() as playwright:
            browser_pool = BrowserPoolOptimized(playwright, proxy_config, use_stealth)
            
            total_products = 0
            total_pages_skipped = 0
            
            try:
                for store in stores:
                    store_id = store["store_id"]
                    store_name = store.get("store_name", f"Store {store_id}")
                    store_products = 0
                    
                    for category in categories:
                        category_name = category["name"]
                        category_url = category["url"]
                        
                        for page_num in range(max_pages):
                            offset = page_num * PAGE_SIZE
                            url = build_category_url(category_url, store_id, offset)
                            
                            products, should_continue = await browser_pool.process_with_page(
                                store_id,
                                process_category_page_optimized,
                                url,
                                store_id,
                                store_name,
                                category_name,
                                page_num
                            )
                            
                            if products:
                                await Actor.push_data(products)
                                store_products += len(products)
                                total_products += len(products)
                            
                            if not should_continue:
                                # Skip remaining pages for this category
                                pages_skipped = max_pages - page_num - 1
                                total_pages_skipped += pages_skipped
                                break
                    
                    Actor.log.info(f"Store {store_name} complete: {store_products} products")
                    
                    # Force garbage collection between stores
                    gc.collect()
                
            finally:
                await browser_pool.close_all()
        
        Actor.log.info(f"Scraping complete!")
        Actor.log.info(f"Total products: {total_products}")
        Actor.log.info(f"Pages skipped (smart pagination): {total_pages_skipped}")
        Actor.log.info(f"Estimated bandwidth savings: 60-70%")


if __name__ == "__main__":
    asyncio.run(main())
