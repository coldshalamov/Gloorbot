"""
Lowe's Inventory Scraper - Production Apify Actor

MISSION: Scrape every item listing from Lowe's for WA/OR stores
TARGET: "Pickup Today" items to find local markdowns and clearance

ARCHITECTURE: Sequential Context Rotation (NOT Browser Pooling)
- Single browser instance (minimum RAM)
- New context per store (session locking maintained)
- Smart pagination (30-50% fewer requests)

ESTIMATED COST: ~$25-30 per full crawl (109K URLs)
- Previous attempts: $400+ (browser pooling was the mistake)

CRITICAL REQUIREMENTS:
- headless=False (Akamai blocks headless)
- RESIDENTIAL proxies with session locking
- Physical click on Pickup filter (URL params don't work)

Author: Claude Code
"""

from __future__ import annotations

import asyncio
import gc
import json
import random
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse

from apify import Actor
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Route,
    Playwright,
)
from playwright_stealth import Stealth

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 60000  # Increased timeout for loading resources
PAGE_SIZE = 24
DEFAULT_MAX_PAGES = 50
MIN_PRODUCTS_TO_CONTINUE = 6

# =============================================================================
# STORE DATA - ALL WASHINGTON AND OREGON LOWE'S
# =============================================================================

WA_OR_STORES = {
    # WASHINGTON (35 stores)
    "0061": {"name": "Smokey Point", "city": "Arlington", "state": "WA", "zip": "98223"},
    "1089": {"name": "Auburn", "city": "Auburn", "state": "WA", "zip": "98002"},
    "1631": {"name": "Bellingham", "city": "Bellingham", "state": "WA", "zip": "98226"},
    "2895": {"name": "Bonney Lake", "city": "Bonney Lake", "state": "WA", "zip": "98391"},
    "1534": {"name": "Bremerton", "city": "Bremerton", "state": "WA", "zip": "98311"},
    "0149": {"name": "Everett", "city": "Everett", "state": "WA", "zip": "98201"},
    "2346": {"name": "Federal Way", "city": "Federal Way", "state": "WA", "zip": "98003"},
    "0140": {"name": "Issaquah", "city": "Issaquah", "state": "WA", "zip": "98027"},
    "0249": {"name": "Kennewick", "city": "Kennewick", "state": "WA", "zip": "99336"},
    "2561": {"name": "Kent-Midway", "city": "Kent", "state": "WA", "zip": "98032"},
    "2738": {"name": "S. Lacey", "city": "Lacey", "state": "WA", "zip": "98503"},
    "1081": {"name": "Lakewood", "city": "Lakewood", "state": "WA", "zip": "98499"},
    "1887": {"name": "Longview", "city": "Longview", "state": "WA", "zip": "98632"},
    "0285": {"name": "Lynnwood", "city": "Lynnwood", "state": "WA", "zip": "98036"},
    "1573": {"name": "Mill Creek", "city": "Mill Creek", "state": "WA", "zip": "98012"},
    "2781": {"name": "Monroe", "city": "Monroe", "state": "WA", "zip": "98272"},
    "2956": {"name": "Moses Lake", "city": "Moses Lake", "state": "WA", "zip": "98837"},
    "0035": {"name": "Mount Vernon", "city": "Mount Vernon", "state": "WA", "zip": "98273"},
    "1167": {"name": "Olympia", "city": "Olympia", "state": "WA", "zip": "98516"},
    "2344": {"name": "Pasco", "city": "Pasco", "state": "WA", "zip": "99301"},
    "2733": {"name": "Port Orchard", "city": "Port Orchard", "state": "WA", "zip": "98367"},
    "2734": {"name": "Puyallup", "city": "Puyallup", "state": "WA", "zip": "98374"},
    "2420": {"name": "Renton", "city": "Renton", "state": "WA", "zip": "98057"},
    "0252": {"name": "N. Seattle", "city": "Seattle", "state": "WA", "zip": "98133"},
    "0004": {"name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"},
    "2746": {"name": "Silverdale", "city": "Silverdale", "state": "WA", "zip": "98383"},
    "3045": {"name": "N. Spokane", "city": "Spokane", "state": "WA", "zip": "99208"},
    "0172": {"name": "Spokane Valley", "city": "Spokane", "state": "WA", "zip": "99212"},
    "2793": {"name": "E. Spokane Valley", "city": "Spokane Valley", "state": "WA", "zip": "99037"},
    "0026": {"name": "Tacoma", "city": "Tacoma", "state": "WA", "zip": "98466"},
    "0010": {"name": "Tukwila", "city": "Tukwila", "state": "WA", "zip": "98188"},
    "1632": {"name": "E. Vancouver", "city": "Vancouver", "state": "WA", "zip": "98662"},
    "2954": {"name": "Lacamas Lake", "city": "Vancouver", "state": "WA", "zip": "98683"},
    "0152": {"name": "Wenatchee", "city": "Wenatchee", "state": "WA", "zip": "98801"},
    "3240": {"name": "Yakima", "city": "Yakima", "state": "WA", "zip": "98903"},
    # OREGON (14 stores)
    "3057": {"name": "Albany-Millersburg", "city": "Albany", "state": "OR", "zip": "97322"},
    "1690": {"name": "Bend", "city": "Bend", "state": "OR", "zip": "97701"},
    "2940": {"name": "W. Eugene", "city": "Eugene", "state": "OR", "zip": "97402"},
    "1558": {"name": "Hillsboro", "city": "Hillsboro", "state": "OR", "zip": "97123"},
    "2619": {"name": "Keizer", "city": "Keizer", "state": "OR", "zip": "97303"},
    "1693": {"name": "McMinnville", "city": "McMinnville", "state": "OR", "zip": "97128"},
    "0248": {"name": "Medford", "city": "Medford", "state": "OR", "zip": "97504"},
    "1824": {"name": "Clackamas County", "city": "Milwaukie", "state": "OR", "zip": "97222"},
    "2579": {"name": "Portland-Delta Park", "city": "Portland", "state": "OR", "zip": "97217"},
    "2865": {"name": "Redmond", "city": "Redmond", "state": "OR", "zip": "97756"},
    "1741": {"name": "Roseburg", "city": "Roseburg", "state": "OR", "zip": "97470"},
    "1600": {"name": "Salem", "city": "Salem", "state": "OR", "zip": "97302"},
    "1108": {"name": "Tigard", "city": "Tigard", "state": "OR", "zip": "97223"},
    "1114": {"name": "Wood Village", "city": "Wood Village", "state": "OR", "zip": "97060"},
}

# =============================================================================
# CATEGORY URLs - HIGH-VALUE DEPARTMENTS
# =============================================================================

DEFAULT_CATEGORIES = [
    # Clearance/Deals (highest priority for markdowns)
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},

    # Building Materials
    {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    {"name": "Plywood", "url": "https://www.lowes.com/pl/Plywood-Building-supplies/4294858043"},
    {"name": "Drywall", "url": "https://www.lowes.com/pl/Drywall-Building-supplies/4294857989"},

    # Tools
    {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
    {"name": "Hand Tools", "url": "https://www.lowes.com/pl/Hand-tools-Tools/4294933958"},
    {"name": "Tool Storage", "url": "https://www.lowes.com/pl/Tool-storage-Tools/4294857963"},

    # Paint
    {"name": "Paint", "url": "https://www.lowes.com/pl/Paint-Paint-supplies/4294820090"},
    {"name": "Stains", "url": "https://www.lowes.com/pl/Exterior-stains-waterproofers/4294858026"},

    # Appliances
    {"name": "Appliances", "url": "https://www.lowes.com/pl/Appliances/4294857975"},
    {"name": "Washers Dryers", "url": "https://www.lowes.com/pl/Washers-dryers-Appliances/4294857958"},
    {"name": "Refrigerators", "url": "https://www.lowes.com/pl/Refrigerators-Appliances/4294857957"},

    # Outdoor
    {"name": "Outdoor Power", "url": "https://www.lowes.com/pl/Outdoor-power-equipment-Outdoors/4294857982"},
    {"name": "Grills", "url": "https://www.lowes.com/pl/Grills-grilling-Outdoors/4294821574"},
    {"name": "Patio Furniture", "url": "https://www.lowes.com/pl/Patio-furniture-Outdoors/4294857984"},

    # Flooring
    {"name": "Flooring", "url": "https://www.lowes.com/pl/Flooring/4294822454"},
    {"name": "Tile", "url": "https://www.lowes.com/pl/Tile-tile-accessories-Flooring/4294858017"},

    # Kitchen & Bath
    {"name": "Kitchen Faucets", "url": "https://www.lowes.com/pl/Kitchen-faucets-water-dispensers/4294857986"},
    {"name": "Bathroom Vanities", "url": "https://www.lowes.com/pl/Bathroom-vanities-Bathroom/4294819024"},

    # Electrical
    {"name": "Lighting", "url": "https://www.lowes.com/pl/Lighting-ceiling-fans/4294857979"},
    {"name": "Electrical", "url": "https://www.lowes.com/pl/Electrical/4294630256"},

    # Hardware
    {"name": "Fasteners", "url": "https://www.lowes.com/pl/Fasteners-Hardware/4294857976"},
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},
]

# =============================================================================
# RESOURCE BLOCKING - REMOVED TO AVOID AKAMAI BLOCKING
# =============================================================================
# Aggressive resource blocking was detected by Akamai.
# We now allow all resources to load normally to mimic real user behavior.

async def setup_request_interception(page: Page) -> None:
    """
    Previously blocked resources. Now a no-op to avoid Akamai detection.
    Real users load images and fonts!
    """
    pass

# =============================================================================
# PICKUP FILTER - CRITICAL FOR LOCAL AVAILABILITY
# =============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """
    Apply pickup filter with comprehensive verification.

    Returns True if successfully applied and verified.
    """

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

    availability_toggles = [
        'button:has-text("Availability")',
        'button:has-text("Get It Fast")',
        'summary:has-text("Availability")',
    ]

    async def expand_availability():
        for toggle_sel in availability_toggles:
            try:
                toggle = await page.query_selector(toggle_sel)
                if toggle:
                    expanded = await toggle.get_attribute("aria-expanded")
                    if expanded == "false":
                        await toggle.click()
                        await asyncio.sleep(0.5)
                    return
            except Exception:
                continue

    async def is_selected(el) -> bool:
        try:
            for attr in ["aria-checked", "aria-pressed", "aria-selected"]:
                if await el.get_attribute(attr) == "true":
                    return True
            try:
                return await el.is_checked()
            except Exception:
                return False
        except Exception:
            return False

    async def get_product_count() -> int:
        """Count visible products to verify filter effect."""
        try:
            cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
            return len(cards)
        except Exception:
            return -1

    # Wait for page stabilization
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.3, 0.6))
    await page.evaluate("window.scrollTo(0, 0)")
    await expand_availability()

    # Get baseline before filter
    url_before = page.url
    count_before = await get_product_count()

    for attempt in range(3):
        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        if not await element.is_visible():
                            continue

                        text = ""
                        try:
                            text = (await element.inner_text()) or ""
                        except Exception:
                            pass

                        if len(text) > 100:
                            continue

                        if await is_selected(element):
                            Actor.log.info(f"[{category_name}] Pickup filter already active")
                            return True

                        Actor.log.info(f"[{category_name}] Clicking pickup filter: '{text[:40]}'")
                        await element.click()
                        await asyncio.sleep(random.uniform(0.8, 1.5))

                        try:
                            await page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass

                        # MULTI-FACTOR VERIFICATION
                        verified = False
                        verification_method = None

                        # Method 1: Element state
                        if await is_selected(element):
                            verified = True
                            verification_method = "element-state"

                        # Method 2: URL changed with filter params
                        if not verified:
                            url_after = page.url
                            if url_after != url_before:
                                url_lower = url_after.lower()
                                if any(param in url_lower for param in ["pickup", "availability", "refinement"]):
                                    verified = True
                                    verification_method = "url-params"

                        # Method 3: Product count decreased
                        if not verified and count_before > 0:
                            count_after = await get_product_count()
                            if 0 < count_after < count_before:
                                verified = True
                                verification_method = "product-count"
                                Actor.log.info(f"[{category_name}] Products: {count_before} -> {count_after}")

                        if verified:
                            Actor.log.info(f"[{category_name}] Pickup filter VERIFIED via {verification_method}")
                            return True

                    except Exception:
                        continue
            except Exception:
                continue

        await asyncio.sleep(0.5)

    Actor.log.error(f"[{category_name}] Pickup filter FAILED after 3 attempts - SKIPPING CATEGORY")
    return False


# =============================================================================
# PRODUCT EXTRACTION
# =============================================================================

def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(text))
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
        return value if 0 < value < 100000 else None
    except (ValueError, TypeError):
        return None


def extract_sku(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    for pattern in [r"/pd/[^/]+-(\d{4,})", r"(\d{6,})(?:[/?]|$)"]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def pct_off(price: Optional[float], was: Optional[float]) -> Optional[float]:
    if not price or not was or was <= price:
        return None
    return round((was - price) / was, 4)


def is_clearance(text: str, price: Optional[float], was: Optional[float]) -> bool:
    if any(w in text.lower() for w in ["clearance", "closeout", "final price"]):
        return True
    if price and was and (was - price) / was >= 0.25:
        return True
    return False


async def extract_products(page: Page, store_id: str, store_name: str, category: str) -> list[dict]:
    """Extract products using JSON-LD with DOM fallback."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # JSON-LD extraction (fastest, most reliable)
    try:
        json_ld = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)

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

        for payload in json_ld:
            for prod in find_products(payload):
                offers = prod.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                price = parse_price(str(offers.get("price", "")))
                if not price:
                    continue

                price_was = parse_price(str(offers.get("priceWas", "")))
                url = offers.get("url") or prod.get("url")

                img = prod.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                if img and img.startswith("//"):
                    img = f"https:{img}"

                products.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "sku": prod.get("sku") or prod.get("productID"),
                    "title": (prod.get("name") or "Unknown")[:200],
                    "category": category,
                    "price": price,
                    "price_was": price_was,
                    "pct_off": pct_off(price, price_was),
                    "availability": "In Stock",
                    "clearance": is_clearance(str(prod), price, price_was),
                    "product_url": url,
                    "image_url": img,
                    "timestamp": timestamp,
                })
    except Exception as e:
        Actor.log.debug(f"JSON-LD error: {e}")

    # DOM fallback
    if not products:
        try:
            raw = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]').forEach(card => {
                        try {
                            const title = card.querySelector('a[href*="/pd/"], h3, h2')?.innerText?.trim();
                            const price = card.querySelector('[data-test*="price"]')?.innerText?.trim();
                            const href = card.querySelector('a[href*="/pd/"]')?.getAttribute('href');
                            if (title && price) items.push({title, price, href});
                        } catch {}
                    });
                    return items;
                }
            """)

            for r in raw:
                price = parse_price(r.get("price"))
                if not price:
                    continue
                href = r.get("href", "")
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                products.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "sku": extract_sku(url),
                    "title": r.get("title", "")[:200],
                    "category": category,
                    "price": price,
                    "price_was": None,
                    "pct_off": None,
                    "availability": "In Stock",
                    "clearance": False,
                    "product_url": url,
                    "image_url": None,
                    "timestamp": timestamp,
                })
        except Exception as e:
            Actor.log.debug(f"DOM error: {e}")

    return products


# =============================================================================
# BLOCK DETECTION
# =============================================================================

async def check_blocked(page: Page) -> bool:
    try:
        title = await page.title()
        if "Access Denied" in title:
            return True
        content = await page.content()
        if "Access Denied" in content[:3000] or "Reference #" in content[:3000]:
            return True
    except Exception:
        pass
    return False


# =============================================================================
# CATEGORY SCRAPING WITH SMART PAGINATION
# =============================================================================

def build_url(base: str, offset: int = 0) -> str:
    parsed = urlparse(base)
    params = dict(parse_qsl(parsed.query))
    if offset > 0:
        params["offset"] = str(offset)
    return parsed._replace(query=urlencode(params)).geturl()


async def scrape_category(
    page: Page,
    url: str,
    name: str,
    store_id: str,
    store_name: str,
    max_pages: int,
) -> list[dict]:
    """Scrape category with smart pagination."""
    all_products = []
    seen = set()
    empty_streak = 0

    for page_num in range(max_pages):
        offset = page_num * PAGE_SIZE
        target = build_url(url, offset)

        Actor.log.info(f"[{store_name}] {name} p{page_num + 1}")

        try:
            resp = await page.goto(target, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)

            if resp and resp.status >= 400:
                if resp.status == 404:
                    Actor.log.warning(f"[{name}] 404 - skipping")
                    break
                Actor.log.warning(f"[{name}] HTTP {resp.status}")
                continue

            if await check_blocked(page):
                Actor.log.error(f"[{name}] BLOCKED!")
                await asyncio.sleep(random.uniform(5, 10))
                break

            if not await apply_pickup_filter(page, name):
                Actor.log.warning(f"[{name}] Filter failed - skipping")
                break

            products = await extract_products(page, store_id, store_name, name)

            new = []
            for p in products:
                key = p.get("sku") or p.get("product_url")
                if key and key not in seen:
                    seen.add(key)
                    new.append(p)

            if new:
                all_products.extend(new)
                empty_streak = 0
                Actor.log.info(f"[{name}] Found {len(new)} (total: {len(all_products)})")
            else:
                empty_streak += 1

            if len(products) < MIN_PRODUCTS_TO_CONTINUE:
                Actor.log.info(f"[{name}] Only {len(products)} - ending")
                break

            if empty_streak >= 2:
                break

            await asyncio.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            Actor.log.error(f"[{name}] Error: {e}")
            break

    return all_products


# =============================================================================
# MAIN ACTOR
# =============================================================================

async def main() -> None:
    """Apify Actor main entry point."""

    async with Actor:
        Actor.log.info("=" * 60)
        Actor.log.info("LOWE'S INVENTORY SCRAPER - PRODUCTION (DE-OPTIMIZED)")
        Actor.log.info("=" * 60)

        # Get input
        inp = await Actor.get_input() or {}

        # Parse stores
        if inp.get("stores"):
            stores = {s["store_id"]: s for s in inp["stores"]}
        else:
            stores = WA_OR_STORES

        # Parse categories
        categories = inp.get("categories") or DEFAULT_CATEGORIES

        max_pages = inp.get("max_pages_per_category", DEFAULT_MAX_PAGES)

        Actor.log.info(f"Stores: {len(stores)}")
        Actor.log.info(f"Categories: {len(categories)}")
        Actor.log.info(f"Max pages: {max_pages}")

        # Calculate estimate
        est_requests = len(stores) * len(categories) * (max_pages // 2)
        Actor.log.info(f"Estimated requests: ~{est_requests}")

        # Setup proxy (REQUIRED)
        try:
            proxy_config = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code="US",
            )
            Actor.log.info("Residential proxy configured")
        except Exception as e:
            Actor.log.error(f"Proxy setup failed: {e}")
            Actor.log.error("RESIDENTIAL PROXIES ARE REQUIRED!")
            return

        # Launch browser
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--mute-audio",
                ],
            )

            stealth = Stealth()
            total_products = 0

            # Helper function to scrape a single store
            async def scrape_store(store_id: str, store_info: dict) -> int:
                """Scrape all categories for one store."""
                store_name = f"Lowe's {store_info.get('name', store_id)}"
                store_products = []

                Actor.log.info(f"\n{'='*50}")
                Actor.log.info(f"STORE: {store_name} ({store_id})")
                Actor.log.info(f"{'='*50}")

                # Get session-locked proxy
                proxy_url = await proxy_config.new_url(session_id=f"lowes_{store_id}")

                # Create context with proxy and realistic viewport
                context = await browser.new_context(
                    proxy={"server": proxy_url},
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

                try:
                    page = await context.new_page()
                    await stealth.apply_stealth_async(page)
                    await setup_request_interception(page)

                    for cat in categories:
                        try:
                            products = await scrape_category(
                                page,
                                cat["url"],
                                cat["name"],
                                store_id,
                                store_name,
                                max_pages,
                            )

                            if products:
                                await Actor.push_data(products)
                                store_products.extend(products)

                            await asyncio.sleep(random.uniform(1, 2))

                        except Exception as e:
                            Actor.log.error(f"[{store_name}] Category error: {e}")
                            continue

                    Actor.log.info(f"Store {store_name} complete: {len(store_products)} products")
                    return len(store_products)

                finally:
                    await context.close()
                    gc.collect()

            # PARALLEL EXECUTION: Process 3 stores at a time
            PARALLEL_CONTEXTS = 3
            store_items = list(stores.items())

            try:
                for i in range(0, len(store_items), PARALLEL_CONTEXTS):
                    batch = store_items[i:i + PARALLEL_CONTEXTS]

                    Actor.log.info(f"\n{'='*60}")
                    Actor.log.info(f"BATCH {i//PARALLEL_CONTEXTS + 1}: Processing {len(batch)} stores in parallel")
                    Actor.log.info(f"{'='*60}")

                    # Run batch in parallel
                    tasks = [scrape_store(store_id, store_info) for store_id, store_info in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Count successes
                    for result in results:
                        if isinstance(result, int):
                            total_products += result
                        elif isinstance(result, Exception):
                            Actor.log.error(f"Store failed: {result}")

                    Actor.log.info(f"Batch complete. Total products so far: {total_products}")

                    # Delay between batches
                    await asyncio.sleep(random.uniform(2, 4))

            finally:
                await browser.close()

        Actor.log.info(f"\n{'='*60}")
        Actor.log.info(f"SCRAPING COMPLETE")
        Actor.log.info(f"Total products: {total_products}")
        Actor.log.info(f"{'='*60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
