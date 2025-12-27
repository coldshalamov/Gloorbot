"""
Lowe's Full Catalog Scraper - WA/OR Stores

PROVEN WORKING APPROACH:
✅ Chrome channel (NOT Chromium)
✅ Persistent browser profiles
✅ Homepage warmup with human behavior
✅ NO playwright-stealth (red flag!)
✅ NO fingerprint injection (makes it worse!)

PURPOSE:
Clone entire product catalog from WA/OR Lowe's stores to find local markdowns.
Scrapes "pickup today" products from every department in every store.
"""

from __future__ import annotations

import asyncio
import re
import random
from datetime import datetime
from pathlib import Path

from apify import Actor
from playwright.async_api import async_playwright, Page


# ============================================================================
# CONFIG
# ============================================================================

LOWES_MAP_PATH = Path(__file__).parent.parent / "LowesMap.txt"


# ============================================================================
# LOAD STORES & CATEGORIES
# ============================================================================

def load_stores_and_categories():
    """Load WA/OR stores and all category URLs from LowesMap.txt"""
    stores = []
    categories = []

    if not LOWES_MAP_PATH.exists():
        Actor.log.warning(f"LowesMap.txt not found at {LOWES_MAP_PATH}")
        return stores, categories

    with open(LOWES_MAP_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('This') or line.startswith('##'):
                continue

            # Store URLs
            if '/store/' in line:
                match = re.search(r'/store/([A-Z]{2})-([^/]+)/(\d+)', line)
                if match:
                    state, city, store_id = match.groups()
                    stores.append({
                        "url": line,
                        "store_id": store_id,
                        "city": city.replace('-', ' '),
                        "state": state,
                        "name": f"{city}, {state} (#{store_id})"
                    })

            # Category URLs (skip clearance)
            elif '/pl/' in line and 'the-back-aisle' not in line.lower():
                categories.append(line)

    Actor.log.info(f"Loaded {len(stores)} stores and {len(categories)} categories")
    return stores, categories


# ============================================================================
# HUMAN BEHAVIOR
# ============================================================================

async def human_mouse_move(page: Page):
    """Human-like mouse movement"""
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
    """CRITICAL: Visit homepage with human behavior to establish trust"""
    Actor.log.info("Warming up session...")

    await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)

    await human_mouse_move(page)
    await asyncio.sleep(1 + random.random())
    await human_scroll(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)
    await human_mouse_move(page)
    await asyncio.sleep(0.5 + random.random() * 0.5)

    Actor.log.info("Warmup complete")


async def set_store_context(page: Page, store_url: str, store_name: str):
    """Set store for pricing/availability"""
    Actor.log.info(f"Setting store: {store_name}")

    await page.goto(store_url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(2)

    for selector in ["button:has-text('Set Store')", "button:has-text('Set as My Store')"]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click(timeout=8000)
                await asyncio.sleep(1.5)
                Actor.log.info(f"Store set successfully")
                return True
        except:
            continue

    Actor.log.warning("Could not set store")
    return False


# ============================================================================
# SCRAPING
# ============================================================================

async def scrape_category_page(page: Page, url: str, store_info: dict, page_num: int = 1) -> list[dict]:
    """Scrape one page of products"""
    products = []

    # Build URL with pagination
    page_url = url
    if page_num > 1:
        sep = '&' if '?' in url else '?'
        page_url = f"{url}{sep}offset={(page_num - 1) * 24}"

    # Navigate with human behavior
    await asyncio.sleep(0.5 + random.random() * 0.5)

    try:
        await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
    except asyncio.TimeoutError:
        Actor.log.error(f"Navigation timeout on page {page_num} after 60s")
        raise  # Re-raise timeout - browser might be hung
    except Exception as e:
        Actor.log.error(f"Navigation error on page {page_num}: {e}")
        # If browser connection is broken, don't try to continue
        if "closed" in str(e).lower() or "connection" in str(e).lower():
            raise  # Re-raise to stop category scraping
        return []  # Otherwise just skip this page

    await asyncio.sleep(1 + random.random())

    try:
        await human_mouse_move(page)
        await human_scroll(page)
    except Exception as e:
        Actor.log.warning(f"Interaction error on page {page_num}: {e}")
        # Continue even if mouse/scroll fails

    await asyncio.sleep(1)

    # Check for blocking with timeout
    try:
        title = await asyncio.wait_for(page.title(), timeout=10.0)
        if "Access Denied" in title or "Robot" in title or "Blocked" in title:
            Actor.log.error(f"BLOCKED on page {page_num}: {title}")
            raise Exception(f"Blocked by anti-bot: {title}")  # Raise to stop scraping
    except asyncio.TimeoutError:
        Actor.log.error(f"Timeout getting page title on page {page_num} - browser may be hung")
        raise  # Re-raise - this indicates a serious problem

    # Find product cards with timeout
    selectors = ['[class*="ProductCard"]', '[class*="product-card"]', 'article', '[data-test="product-pod"]']
    product_cards = []
    try:
        for sel in selectors:
            cards = await asyncio.wait_for(page.locator(sel).all(), timeout=15.0)
            if len(cards) > len(product_cards):
                product_cards = cards
    except asyncio.TimeoutError:
        Actor.log.error(f"Timeout finding product cards on page {page_num}")
        raise

    if not product_cards:
        Actor.log.warning(f"No product cards found on page {page_num}")
        return []

    # Extract products with timeout per card
    for card_idx, card in enumerate(product_cards):
        try:
            # Wrap entire card extraction in timeout
            async def extract_card():
                # Must have product link
                pd_links = await card.locator("a[href*='/pd/']").all()
                if not pd_links:
                    return None

                href = await pd_links[0].get_attribute("href") or ""
                if not href:
                    return None

                # Title
                title_text = (await pd_links[0].inner_text()).strip()
                if not title_text:
                    title_el = card.locator(":scope [data-testid='item-description'], :scope h3, :scope h2").first
                    if await title_el.count() > 0:
                        title_text = await title_el.inner_text()

                # Price
                price_text = ""
                price_el = card.locator(":scope [data-testid='current-price'], :scope [data-test*='price']").first
                if await price_el.count() > 0:
                    price_text = await price_el.inner_text()

                # Was price (markdown indicator)
                was_price = ""
                was_el = card.locator(":scope [data-testid='was-price'], :scope [data-test*='was']").first
                if await was_el.count() > 0:
                    was_price = await was_el.inner_text()

                if title_text and href and len(title_text) > 5:
                    return {
                        "title": title_text.strip(),
                        "price": price_text.strip() if price_text else "N/A",
                        "was_price": was_price.strip() if was_price else "",
                        "has_markdown": bool(was_price),
                        "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
                        "store_id": store_info["store_id"],
                        "store_name": store_info["name"],
                        "store_city": store_info["city"],
                        "store_state": store_info["state"],
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                return None

            product = await asyncio.wait_for(extract_card(), timeout=5.0)
            if product:
                products.append(product)

        except asyncio.TimeoutError:
            Actor.log.warning(f"Timeout extracting card {card_idx} on page {page_num}")
            continue  # Skip this card
        except Exception as e:
            # Log unexpected errors but continue
            if card_idx == 0:  # Only log first card error to avoid spam
                Actor.log.warning(f"Error extracting card on page {page_num}: {e}")
            continue

    return products


async def scrape_category_all_pages(page: Page, category_url: str, store_info: dict) -> list[dict]:
    """Scrape ALL pages of a category until no more products found"""
    all_products = []
    cat_name = category_url.split('/pl/')[-1].split('/')[0][:30]

    page_num = 1
    while True:  # Scrape until we run out of products
        try:
            # Add per-page timeout to prevent infinite hangs
            products = await asyncio.wait_for(
                scrape_category_page(page, category_url, store_info, page_num),
                timeout=120.0  # 2 minutes max per page
            )

            if not products:
                # No products found - we've reached the end
                break

            all_products.extend(products)
            Actor.log.info(f"{store_info['name']} - {cat_name} p{page_num}: {len(products)} products")

            # Stop if partial page (end of results)
            if len(products) < 12:
                break

            page_num += 1

        except asyncio.TimeoutError:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: TIMEOUT after 120s")
            # Stop scraping this category if a page times out
            break
        except Exception as e:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: Error - {e}")
            # Stop scraping this category on error
            break

    if all_products:
        Actor.log.info(f"{store_info['name']} - {cat_name}: {len(all_products)} total products from {page_num} pages")

    return all_products


# ============================================================================
# MAIN
# ============================================================================

async def main():
    async with Actor:
        # Input
        actor_input = await Actor.get_input() or {}
        test_mode = actor_input.get("testMode", False)
        max_stores = actor_input.get("maxStores", 1 if test_mode else 999)
        max_categories = actor_input.get("maxCategories", 2 if test_mode else 999)
        proxy_url = actor_input.get("proxyUrl")  # External proxy
        state_filter = actor_input.get("stateFilter", ["WA", "OR"])

        Actor.log.info("=" * 70)
        Actor.log.info("Lowe's Full Catalog Scraper")
        Actor.log.info("=" * 70)
        Actor.log.info(f"Test mode: {test_mode}")
        Actor.log.info(f"Max stores: {max_stores}")
        Actor.log.info(f"Max categories: {max_categories}")
        if proxy_url:
            Actor.log.info(f"Proxy: {proxy_url}")

        # Load data
        all_stores, all_categories = load_stores_and_categories()

        # Filter by state
        if state_filter:
            all_stores = [s for s in all_stores if s["state"] in state_filter]

        stores = all_stores[:max_stores]
        categories = all_categories[:max_categories]

        Actor.log.info(f"Scraping {len(stores)} stores x {len(categories)} categories")

        # Scrape each store sequentially (parallel causes blocking)
        total_products = 0

        async with async_playwright() as p:
            for store in stores:
                Actor.log.info(f"\n{'='*70}")
                Actor.log.info(f"Starting store: {store['name']}")
                Actor.log.info(f"{'='*70}")

                # Browser setup
                profile_dir = Path(f".playwright-profiles/store-{store['store_id']}")
                profile_dir.mkdir(parents=True, exist_ok=True)

                launch_kwargs = {
                    "headless": False,  # CRITICAL: Must be False
                    "channel": "chrome",
                    "viewport": {"width": 1440, "height": 900},
                    "locale": "en-US",
                    "timezone_id": "America/Los_Angeles",
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-infobars",
                        "--disable-gpu",  # Reduce GPU process overhead
                        "--no-sandbox",  # Reduce process spawning
                        "--disable-background-networking",  # Prevent background resource usage
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--memory-pressure-off",  # Prevent memory-based crashes
                    ]
                }

                if proxy_url:
                    launch_kwargs["proxy"] = {"server": proxy_url}

                context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
                page = context.pages[0] if context.pages else await context.new_page()

                try:
                    # Setup
                    await warmup_session(page)
                    await set_store_context(page, store["url"], store["name"])

                    # Scrape categories
                    store_products = []
                    for idx, category_url in enumerate(categories):
                        try:
                            products = await scrape_category_all_pages(page, category_url, store)
                            store_products.extend(products)

                            # Push incrementally
                            if products:
                                await Actor.push_data(products)

                            await asyncio.sleep(1)

                        except Exception as e:
                            # Log the error but continue with next category
                            Actor.log.error(f"Error scraping category {idx}: {e}")
                            # If it's a timeout or browser crash, this category failed - move on
                            continue

                    total_products += len(store_products)
                    Actor.log.info(f"Store complete: {len(store_products)} products from {store['name']}")

                except Exception as e:
                    Actor.log.error(f"Error scraping {store['name']}: {e}")
                finally:
                    await context.close()

        Actor.log.info("=" * 70)
        Actor.log.info(f"ALL DONE! Total products: {total_products}")
        Actor.log.info("=" * 70)
