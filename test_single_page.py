"""
Test scraping with updated selectors
"""
import asyncio
import random
import re
from pathlib import Path
from playwright.async_api import async_playwright


async def human_mouse_move(page):
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
        await asyncio.sleep(0.02)


async def human_scroll(page):
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep(0.05)


async def main():
    profile_dir = Path(".playwright-profiles/test-updated-selectors")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        launch_kwargs = {
            "headless": False,
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
            ],
        }

        try:
            context = await p.chromium.launch_persistent_context(str(profile_dir), channel="chrome", **launch_kwargs)
            print("[INFO] Using Chrome")
        except:
            context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
            print("[INFO] Using Chromium")

        page = context.pages[0] if context.pages else await context.new_page()

        try:
            # Warmup
            print("\n[STEP 1] Warming up...")
            await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)
            await human_mouse_move(page)
            await asyncio.sleep(1)
            await human_scroll(page)
            await asyncio.sleep(2)

            # Go to category with pickup filter already applied
            print("\n[STEP 2] Going to category page with pickup filter...")
            url = "https://www.lowes.com/pl/power-tools/4294607842?inStock=1&rollUpVariants=0"
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)
            await human_mouse_move(page)
            await asyncio.sleep(1)
            await human_scroll(page)
            await asyncio.sleep(2)

            title = await page.title()
            print(f"[INFO] Page title: {title}")

            if "Access Denied" in title:
                print("[ERROR] BLOCKED!")
                await context.close()
                return

            # Test with div.tile_group selector
            print("\n[STEP 3] Finding product cards with div.tile_group...")

            cards = await page.locator('div.tile_group').all()
            print(f"[INFO] Found {len(cards)} product tiles")

            # Extract data from each card
            products = []
            money_re = re.compile(r"\$([0-9]{1,5})(?:\.([0-9]{2}))?")

            for i, card in enumerate(cards[:10]):
                try:
                    # Link
                    link_el = card.locator("a[href*='/pd/']").first
                    if await link_el.count() == 0:
                        continue
                    href = await link_el.get_attribute("href") or ""

                    # Title using Lowe's data-selector
                    title_el = card.locator("[data-selector='splp-prd-ttl']").first
                    if await title_el.count() > 0:
                        title_text = (await title_el.inner_text()).strip()
                    else:
                        title_text = (await link_el.inner_text()).strip()

                    # Current price using Lowe's data-selector
                    price_text = ""
                    for sel in ["[data-selector='splp-prd-act-$']", "[data-selector='splp-prd-$']"]:
                        price_el = card.locator(sel).first
                        if await price_el.count() > 0:
                            price_text = (await price_el.inner_text()).strip()
                            if '$' in price_text:
                                break

                    # Was price using Lowe's data-selector
                    was_text = ""
                    was_el = card.locator("[data-selector='splp-prd-promo-was-$']").first
                    if await was_el.count() > 0:
                        was_text = (await was_el.inner_text()).strip()

                    # Parse prices
                    def parse_price(text):
                        if not text:
                            return None
                        compact = re.sub(r"\s+", "", text)
                        m = money_re.search(compact)
                        if m:
                            whole = m.group(1)
                            cents = m.group(2) or "00"
                            return float(f"{whole}.{cents}")
                        return None

                    price = parse_price(price_text)
                    was_price = parse_price(was_text)

                    if title_text and href:
                        pct_off = 0
                        if price and was_price and was_price > price:
                            pct_off = round((was_price - price) / was_price * 100, 1)

                        products.append({
                            "title": title_text[:60],
                            "price": f"${price:.2f}" if price else "N/A",
                            "was_price": f"${was_price:.2f}" if was_price else "",
                            "pct_off": pct_off,
                            "url": href[:50],
                        })

                except Exception as e:
                    print(f"  Card {i} error: {e}")
                    continue

            print(f"\n[RESULTS] Found {len(products)} products:")
            for i, p in enumerate(products):
                print(f"\n  {i+1}. {p['title']}...")
                print(f"     Price: {p['price']}, Was: {p['was_price']}, Off: {p['pct_off']}%")

            # Show deals
            markdowns = [p for p in products if p['pct_off'] >= 30]
            print(f"\n[DEALS 30%+ OFF] {len(markdowns)} products:")
            for m in markdowns[:5]:
                print(f"  - {m['title']}: {m['price']} (was {m['was_price']}, {m['pct_off']}% off)")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n[INFO] Closing browser...")
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
