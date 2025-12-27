"""
Lowe's Scraper - Core Browser Logic
Uses ephemeral browser contexts (no persistent disk profiles).
"""
import asyncio
import random
import re
from datetime import datetime
from pathlib import Path

# Mock Actor for local runs
class Actor:
    @staticmethod
    def log_info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def log_warning(msg): print(f"[WARN] {msg}")
    @staticmethod
    def log_error(msg): print(f"[ERROR] {msg}")
    
    class log:
        @staticmethod
        def info(msg): print(f"[INFO] {msg}")
        @staticmethod
        def warning(msg): print(f"[WARN] {msg}")
        @staticmethod
        def error(msg): print(f"[ERROR] {msg}")


def load_urls(urls_file: Path):
    """Load stores and categories from URL file"""
    stores = []
    categories = []
    
    with open(urls_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
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
            elif '/pl/' in line and 'the-back-aisle' not in line.lower():
                categories.append(line)
                
    return stores, categories


async def human_mouse_move(page):
    """Human-like mouse movement"""
    try:
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
    except:
        pass


async def human_scroll(page):
    """Human-like scrolling"""
    try:
        for _ in range(2 + int(random.random() * 3)):
            scroll_amount = 200 + random.random() * 400
            await page.mouse.wheel(0, scroll_amount)
            await asyncio.sleep(0.3 + random.random() * 0.5)
    except:
        pass


async def warmup_session(page):
    """Warm up browser session"""
    try:
        await page.goto("https://www.lowes.com", timeout=60000)
        await asyncio.sleep(2 + random.random() * 2)
        await human_mouse_move(page)
        await human_scroll(page)
        await asyncio.sleep(1)
    except Exception as e:
        Actor.log.warning(f"Warmup issue: {e}")


async def set_store_context(page, store_url, store_name):
    """Navigate to store page to set location context"""
    try:
        await page.goto(store_url, timeout=60000)
        await asyncio.sleep(2 + random.random() * 2)
        await human_mouse_move(page)
        
        title = await page.title()
        if "Access Denied" in title or "Robot" in title:
            raise Exception(f"Blocked on store page: {title}")
            
        Actor.log.info(f"Store context set: {store_name}")
    except Exception as e:
        Actor.log.error(f"Failed to set store context: {e}")
        raise


async def scrape_category_page(page, category_url, store_info, page_num):
    """Scrape a single page of a category"""
    url = f"{category_url}?offset={(page_num - 1) * 24}"
    
    try:
        await page.goto(url, timeout=60000)
    except Exception as e:
        Actor.log.error(f"Navigation failed: {e}")
        raise

    await asyncio.sleep(1 + random.random())

    try:
        await human_mouse_move(page)
        await human_scroll(page)
    except:
        pass

    await asyncio.sleep(1)

    # Check for blocking
    try:
        title = await asyncio.wait_for(page.title(), timeout=10.0)
        if "Access Denied" in title or "Robot" in title or "Blocked" in title:
            raise Exception(f"Blocked: {title}")
    except asyncio.TimeoutError:
        raise Exception("Timeout getting page title")

    # Find product cards
    selectors = ['[class*="ProductCard"]', '[class*="product-card"]', 'article', '[data-test="product-pod"]']
    product_cards = []
    try:
        for sel in selectors:
            cards = await asyncio.wait_for(page.locator(sel).all(), timeout=15.0)
            if len(cards) > len(product_cards):
                product_cards = cards
    except asyncio.TimeoutError:
        raise Exception("Timeout finding product cards")

    if not product_cards:
        return []

    products = []
    for card_idx, card in enumerate(product_cards):
        try:
            async def extract_card():
                pd_links = await card.locator("a[href*='/pd/']").all()
                if not pd_links:
                    return None

                href = await pd_links[0].get_attribute("href") or ""
                if not href:
                    return None

                title_text = (await pd_links[0].inner_text()).strip()
                if not title_text:
                    title_el = card.locator(":scope [data-testid='item-description'], :scope h3, :scope h2").first
                    if await title_el.count() > 0:
                        title_text = await title_el.inner_text()

                price_text = ""
                price_el = card.locator(":scope [data-testid='current-price'], :scope [data-test*='price']").first
                if await price_el.count() > 0:
                    price_text = await price_el.inner_text()

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
            continue
        except Exception:
            continue

    return products


async def scrape_category_all_pages(page, category_url, store_info):
    """Scrape ALL pages of a category"""
    all_products = []
    cat_name = category_url.split('/pl/')[-1].split('/')[0][:30]

    page_num = 1
    while True:
        try:
            products = await asyncio.wait_for(
                scrape_category_page(page, category_url, store_info, page_num),
                timeout=120.0
            )

            if not products:
                break

            all_products.extend(products)
            Actor.log.info(f"{store_info['name']} - {cat_name} p{page_num}: {len(products)} products")

            if len(products) < 12:
                break

            page_num += 1

        except asyncio.TimeoutError:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: TIMEOUT")
            break
        except Exception as e:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: Error - {e}")
            break

    if all_products:
        Actor.log.info(f"{store_info['name']} - {cat_name}: {len(all_products)} total from {page_num} pages")

    return all_products


async def scrape_store(store_info, categories, output_file, checkpoint_file, start_idx=0):
    """Scrape all categories for a single store"""
    from playwright.async_api import async_playwright
    import json
    import tempfile
    
    async with async_playwright() as p:
        # Use temp directory for browser profile (auto-cleans on close)
        with tempfile.TemporaryDirectory() as temp_profile:
            launch_kwargs = {
                "headless": False,
                "channel": "chrome",
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ]
            }
            
            context = await p.chromium.launch_persistent_context(
                temp_profile,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/Los_Angeles",
                **launch_kwargs
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            try:
                await warmup_session(page)
                await set_store_context(page, store_info["url"], store_info["name"])
                
                # Skip to start_idx
                cats_to_scrape = categories[start_idx:]
                
                for idx, category_url in enumerate(cats_to_scrape):
                    actual_idx = start_idx + idx
                    
                    try:
                        products = await scrape_category_all_pages(page, category_url, store_info)
                        
                        # Save products
                        if products:
                            with open(output_file, "a", encoding="utf-8") as f:
                                for item in products:
                                    f.write(json.dumps(item) + "\n")
                            print(f"[PUSH] Saved {len(products)} products to {output_file}")
                        
                        # Update checkpoint
                        with open(checkpoint_file, "w") as f:
                            f.write(str(actual_idx + 1))
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        Actor.log.error(f"Error on category {actual_idx}: {e}")
                        continue
                        
                Actor.log.info(f"Store complete: {store_info['name']}")
                
            except Exception as e:
                Actor.log.error(f"Store error: {e}")
            finally:
                await context.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--state", default="WA")
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--urls-file", default="urls.txt")
    args = parser.parse_args()
    
    urls_path = Path(args.urls_file)
    stores, categories = load_urls(urls_path)
    
    # Find the store
    store = next((s for s in stores if s["store_id"] == args.store_id), None)
    if not store:
        print(f"Store {args.store_id} not found")
        exit(1)
    
    # Check checkpoint
    start_idx = 0
    checkpoint_path = Path(args.checkpoint)
    if checkpoint_path.exists():
        try:
            start_idx = int(checkpoint_path.read_text().strip())
            print(f"Resuming from index {start_idx}")
        except:
            pass
    
    asyncio.run(scrape_store(store, categories, args.output, args.checkpoint, start_idx))
