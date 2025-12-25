"""
Local Lowe's Scraper Runner - For Home/Carrier IP Execution
============================================================

Runs scraper in sequential batches from your home carrier IP.
Safe: 2 concurrent contexts per batch (won't trigger Akamai)
Fast: ~4-5 hours for full crawl
Scheduled: Runs every 48 hours via APScheduler

Usage:
    python local_scraper.py                    # Start scheduler (runs every 48h)
    python local_scraper.py --now              # Run immediately
    python local_scraper.py --stores 0004 1108 # Specific stores
    python local_scraper.py --sqlite output.db # Custom database path
"""

import asyncio
import argparse
import gc
import random
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse

from playwright.async_api import async_playwright, Browser, Page, Route
from playwright_stealth import Stealth
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 45000
PAGE_SIZE = 24
MIN_PRODUCTS_TO_CONTINUE = 6
PARALLEL_CONTEXTS = 2  # REDUCED: 2 is safer for carrier IP than 3

# Store data
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

DEFAULT_CATEGORIES = [
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
    {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    {"name": "Plywood", "url": "https://www.lowes.com/pl/Plywood-Building-supplies/4294858043"},
    {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
    {"name": "Hand Tools", "url": "https://www.lowes.com/pl/Hand-tools-Tools/4294933958"},
    {"name": "Paint", "url": "https://www.lowes.com/pl/Paint-Paint-supplies/4294820090"},
    {"name": "Appliances", "url": "https://www.lowes.com/pl/Appliances/4294857975"},
    {"name": "Lighting", "url": "https://www.lowes.com/pl/Lighting-ceiling-fans/4294857979"},
    {"name": "Flooring", "url": "https://www.lowes.com/pl/Flooring/4294822454"},
    {"name": "Kitchen Faucets", "url": "https://www.lowes.com/pl/Kitchen-faucets-water-dispensers/4294857986"},
]

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_database(db_path: str) -> None:
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_name TEXT NOT NULL,
            sku TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL,
            price_was REAL,
            pct_off REAL,
            availability TEXT,
            clearance INTEGER,
            product_url TEXT,
            image_url TEXT
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON products(timestamp)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_store ON products(store_id)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_sku ON products(sku)
    """)

    conn.commit()
    conn.close()


def save_products(db_path: str, products: list[dict]) -> None:
    """Save products to SQLite."""
    if not products:
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for p in products:
        c.execute("""
            INSERT INTO products
            (timestamp, store_id, store_name, sku, title, category, price, price_was, pct_off, availability, clearance, product_url, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p.get("timestamp"),
            p.get("store_id"),
            p.get("store_name"),
            p.get("sku"),
            p.get("title"),
            p.get("category"),
            p.get("price"),
            p.get("price_was"),
            p.get("pct_off"),
            p.get("availability"),
            1 if p.get("clearance") else 0,
            p.get("product_url"),
            p.get("image_url"),
        ))

    conn.commit()
    conn.close()


# ============================================================================
# RESOURCE BLOCKING
# ============================================================================

async def setup_request_interception(page: Page) -> None:
    """Block images, fonts, analytics but allow Lowe's and Akamai."""
    async def handle_route(route: Route):
        url = route.request.url.lower()
        resource_type = route.request.resource_type

        # Never block Akamai or Lowe's
        if any(p in url for p in ["akamai", "lowes.com", "_sec/", "/akam/"]):
            await route.continue_()
            return

        # Block heavy resources
        if resource_type in {"image", "media", "font"}:
            await route.abort()
            return

        if any(p in url for p in ["analytics", "tracking", "ads", ".woff", ".ttf"]):
            await route.abort()
            return

        await route.continue_()

    await page.route("**/*", handle_route)


# ============================================================================
# HELPERS
# ============================================================================

def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(text))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
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


# ============================================================================
# PRODUCT EXTRACTION
# ============================================================================

async def extract_products(page: Page, store_id: str, store_name: str, category: str) -> list[dict]:
    """Extract products via JSON-LD with DOM fallback."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

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

        if products:
            print(f"[{category}] Extracted {len(products)} via JSON-LD")
            return products

    except Exception as e:
        print(f"[{category}] JSON-LD error: {e}")

    # DOM fallback
    try:
        raw = await page.evaluate("""
            () => {
                const items = [];
                // Try multiple selectors for cards/items
                const selectors = [
                    '[data-test="product-pod"]',
                    '[data-test="productPod"]',
                    'article',
                    'div[class*="ProductCard"]',
                    'div[class*="product-item"]',
                    'li[class*="product"]',
                    'div[id*="product"]'
                ];

                for (const selector of selectors) {
                    const found = document.querySelectorAll(selector);
                    if (found.length > 5) {  // Only accept if found many
                        found.forEach(card => {
                            try {
                                // Extract title - try multiple selectors
                                let title = card.querySelector('a[href*="/pd/"]')?.innerText?.trim() ||
                                           card.querySelector('h3')?.innerText?.trim() ||
                                           card.querySelector('h2')?.innerText?.trim() ||
                                           card.querySelector('span')?.innerText?.trim();

                                // Extract price - try multiple selectors
                                let priceEl = card.querySelector('[data-test*="price"]') ||
                                            card.querySelector('span[class*="price"]') ||
                                            Array.from(card.querySelectorAll('*')).find(el =>
                                                el.innerText && /\\$\\d+/.test(el.innerText)
                                            );
                                let price = priceEl?.innerText?.trim();

                                // Extract href
                                let href = card.querySelector('a[href*="/pd/"]')?.getAttribute('href') ||
                                          card.querySelector('a')?.getAttribute('href');

                                if (title && title.length > 3 && price && href) {
                                    items.push({title: title.substring(0, 200), price, href});
                                }
                            } catch {}
                        });
                        if (items.length > 0) break;
                    }
                }
                return items;
            }
        """)

        for r in raw:
            price = parse_price(r.get("price"))
            if not price:
                continue
            href = r.get("href", "")
            url = f"{BASE_URL}{href}" if href and href.startswith("/") else href

            products.append({
                "store_id": store_id,
                "store_name": store_name,
                "sku": extract_sku(url) if url else None,
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

        if products:
            print(f"[{category}] Extracted {len(products)} via DOM")

    except Exception as e:
        print(f"[{category}] DOM fallback error: {e}")

    return products


# ============================================================================
# PICKUP FILTER
# ============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """Apply pickup filter with verification."""
    pickup_selectors = [
        'label:has-text("Get It Today")',
        'label:has-text("Pickup Today")',
        'button:has-text("Pickup")',
        '[data-testid*="pickup"]',
        '[aria-label*="Pickup"]',
        'input[type="checkbox"][id*="pickup"]',
    ]

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.3, 0.6))

    for selector in pickup_selectors:
        try:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    if not await element.is_visible():
                        continue

                    await element.click()
                    await asyncio.sleep(random.uniform(0.8, 1.5))

                    try:
                        await page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass

                    # Check if applied
                    checked = await element.get_attribute("aria-checked")
                    if checked == "true":
                        print(f"[{category_name}] Pickup filter applied")
                        return True

                except Exception:
                    continue
        except Exception:
            continue

    print(f"[{category_name}] Filter not found, continuing anyway")
    return True  # Don't fail hard


# ============================================================================
# SCRAPING
# ============================================================================

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
    max_pages: int = 10,
) -> list[dict]:
    """Scrape category with smart pagination."""
    all_products = []
    seen = set()
    empty_streak = 0

    for page_num in range(max_pages):
        offset = page_num * PAGE_SIZE
        target = build_url(url, offset)

        print(f"[{store_name}] {name} p{page_num + 1}")

        try:
            resp = await page.goto(target, wait_until="networkidle", timeout=GOTO_TIMEOUT_MS)

            if resp and resp.status >= 400:
                print(f"[{name}] HTTP {resp.status}")
                if resp.status == 404:
                    break
                continue

            print(f"[{name}] Page loaded, status {resp.status if resp else 'unknown'}")
            await asyncio.sleep(1)  # Extra wait for JS rendering

            # Check for block
            try:
                title = await page.title()
                if "Access Denied" in title:
                    print(f"[{name}] BLOCKED")
                    await asyncio.sleep(5)
                    break
            except Exception:
                pass

            await apply_pickup_filter(page, name)

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
                print(f"[{name}] Found {len(new)} products")
            else:
                empty_streak += 1

            if len(products) < MIN_PRODUCTS_TO_CONTINUE:
                break

            if empty_streak >= 2:
                break

            await asyncio.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            print(f"[{name}] Error: {e}")
            break

    return all_products


async def scrape_store(
    browser: Browser,
    store_id: str,
    store_info: dict,
    categories: list[dict],
    max_pages: int = 10,
) -> list[dict]:
    """Scrape all categories for one store."""
    store_name = f"Lowe's {store_info.get('name', store_id)}"
    all_products = []

    print(f"\n{'='*60}")
    print(f"STORE: {store_name} ({store_id})")
    print(f"{'='*60}")

    context = await browser.new_context(viewport={"width": 1280, "height": 720})

    try:
        page = await context.new_page()
        stealth = Stealth()
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
                    all_products.extend(products)

                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"[{store_name}] Category error: {e}")
                continue

        print(f"{store_name} complete: {len(all_products)} products")

    finally:
        await context.close()
        gc.collect()

    return all_products


async def run_scrape(
    stores: dict,
    categories: list[dict],
    db_path: str,
    max_pages: int = 10,
) -> int:
    """Main scrape orchestration."""
    print("\n" + "="*70)
    print("LOWE'S LOCAL SCRAPER - STARTING")
    print(f"Stores: {len(stores)}, Categories: {len(categories)}")
    print("="*70)

    init_database(db_path)
    total_products = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--mute-audio",
            ],
        )

        try:
            store_items = list(stores.items())

            # Process in batches (2 parallel = safe for carrier IP)
            for batch_idx in range(0, len(store_items), PARALLEL_CONTEXTS):
                batch = store_items[batch_idx:batch_idx + PARALLEL_CONTEXTS]

                print(f"\n{'='*70}")
                print(f"BATCH {batch_idx//PARALLEL_CONTEXTS + 1}/{(len(store_items)-1)//PARALLEL_CONTEXTS + 1}")
                print(f"Stores: {', '.join([s[0] for s in batch])}")
                print(f"{'='*70}")

                # Run batch in parallel (2 at a time)
                tasks = [
                    scrape_store(browser, store_id, store_info, categories, max_pages)
                    for store_id, store_info in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for result in results:
                    if isinstance(result, list):
                        save_products(db_path, result)
                        total_products += len(result)
                    elif isinstance(result, Exception):
                        print(f"Batch error: {result}")

                print(f"Batch complete. Total so far: {total_products}")

                # Wait between batches (safer for IP)
                if batch_idx + PARALLEL_CONTEXTS < len(store_items):
                    wait_time = random.uniform(2, 4)
                    print(f"Waiting {wait_time:.1f}s before next batch...")
                    await asyncio.sleep(wait_time)

        finally:
            await browser.close()

    print("\n" + "="*70)
    print(f"SCRAPING COMPLETE - {total_products} products")
    print(f"Database: {db_path}")
    print("="*70)

    return total_products


# ============================================================================
# SCHEDULING
# ============================================================================

def scheduled_scrape():
    """Run scrape on schedule."""
    print(f"\n[SCHEDULER] Starting scrape at {datetime.now()}")
    asyncio.run(run_scrape(WA_OR_STORES, DEFAULT_CATEGORIES, "lowes_products.db"))
    print(f"[SCHEDULER] Next run at {datetime.now() + timedelta(hours=48)}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Local Lowe's scraper for home/carrier IP execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python local_scraper.py                      # Start scheduler (48h cycle)
  python local_scraper.py --now                # Run immediately
  python local_scraper.py --stores 0004 1108   # Specific stores only
  python local_scraper.py --categories Clearance # Specific categories
  python local_scraper.py --sqlite custom.db   # Custom database
  python local_scraper.py --pages 5             # Limit pages per category
        """,
    )

    parser.add_argument("--now", action="store_true", help="Run immediately instead of scheduling")
    parser.add_argument("--stores", nargs="+", help="Specific store IDs to scrape")
    parser.add_argument("--categories", nargs="+", help="Specific category names to scrape")
    parser.add_argument("--sqlite", default="lowes_products.db", help="SQLite database path")
    parser.add_argument("--pages", type=int, default=10, help="Max pages per category")

    args = parser.parse_args()

    # Filter stores if specified
    if args.stores:
        stores = {sid: info for sid, info in WA_OR_STORES.items() if sid in args.stores}
    else:
        stores = WA_OR_STORES

    # Filter categories if specified
    if args.categories:
        categories = [c for c in DEFAULT_CATEGORIES if c["name"] in args.categories]
    else:
        categories = DEFAULT_CATEGORIES

    # Run now or schedule
    if args.now:
        asyncio.run(run_scrape(stores, categories, args.sqlite, args.pages))
    else:
        if BackgroundScheduler is None:
            print("ERROR: APScheduler not installed")
            print("Install with: pip install apscheduler")
            return

        scheduler = BackgroundScheduler()
        scheduler.add_job(scheduled_scrape, "interval", hours=48)

        print(f"Scheduler started. Next run in 48 hours.")
        print(f"Press Ctrl+C to stop.")

        scheduler.start()

        try:
            while True:
                asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
            print("Scheduler stopped")


if __name__ == "__main__":
    main()
