"""
Lowe's Inventory Scraper - WORKING VERSION with Proven Akamai Bypass

PROVEN WORKING APPROACH (tested and verified):
✅ Chrome channel (channel='chrome') - NOT Chromium
✅ Persistent browser profiles (one per store)
✅ Homepage warmup with human behavior (mouse + scroll)
✅ NO playwright-stealth (it's a red flag!)
✅ NO fingerprint injection (makes it worse!)
✅ Simple and effective

This approach gets 29+ products without blocking (verified in test_exact_from_js.py)
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from apify import Actor
from playwright.async_api import async_playwright, Page

# Human behavior functions (from test_final.js - proven working)

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
        # Ease in-out quad
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
    """
    CRITICAL: Warm up session by visiting homepage with human behavior
    This establishes trust with Akamai before scraping
    """
    Actor.log.info("Warming up browser session...")

    # Load homepage first
    await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)

    # Simulate human behavior
    await human_mouse_move(page)
    await asyncio.sleep(1 + random.random())
    await human_scroll(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)
    await human_mouse_move(page)
    await asyncio.sleep(0.5 + random.random() * 0.5)

    Actor.log.info("Session warm-up complete")


async def set_store_context(page: Page, store_url: str):
    """
    Set store context by visiting store page and clicking 'Set Store'
    This makes products load with pricing and availability
    """
    Actor.log.info(f"Setting store context: {store_url}")

    await page.goto(store_url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(2)

    # Try to find and click "Set Store" button
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
                Actor.log.info("Store context set successfully")
                return True
        except:
            continue

    Actor.log.warning("Could not set store context")
    return False


async def scrape_category(page: Page, url: str, category_name: str) -> list[dict]:
    """Scrape one category page with human behavior"""
    products = []

    # Human behavior before navigation
    await asyncio.sleep(1 + random.random())

    # Navigate to category
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)

    # Human behavior after navigation
    await asyncio.sleep(1 + random.random())
    await human_mouse_move(page)
    await human_scroll(page)
    await asyncio.sleep(2)

    # Check if blocked
    title = await page.title()
    if "Access Denied" in title:
        Actor.log.error(f"BLOCKED on {category_name}")
        return []

    # Extract products - try multiple selectors
    # The test_exact_from_js.py found 39 products with these selectors
    selectors_to_try = [
        'article',
        '[class*="ProductCard"]',
        '[class*="product-card"]',
        '[data-test="product-pod"]',
    ]

    product_cards = []
    for selector in selectors_to_try:
        cards = await page.locator(selector).all()
        if len(cards) > len(product_cards):
            product_cards = cards
            Actor.log.info(f"{category_name}: Found {len(product_cards)} elements with '{selector}'")

    if not product_cards:
        Actor.log.warning(f"{category_name}: No products found")
        return []

    extracted_count = 0
    for card in product_cards:
        try:
            # First, check if this card has a product link (filter out navigation)
            pd_links = await card.locator("a[href*='/pd/']").all()
            if not pd_links:
                continue  # Skip non-product elements

            # Extract link
            href = await pd_links[0].get_attribute("href") or ""
            if not href:
                continue

            # Extract title - try the link text first, then other selectors
            title_text = (await pd_links[0].inner_text()).strip()

            if not title_text:
                # Fallback to other selectors
                title_selector = ":scope [data-testid='item-description'], :scope a[data-testid='item-description-link'], :scope [data-test*='product-title'], :scope h3, :scope h2"
                title_el = card.locator(title_selector).first
                if await title_el.count() > 0:
                    title_text = await title_el.inner_text()

            # Extract price using main.js selectors
            price_text = ""
            price_selector = ":scope [data-testid='regular-price'], :scope [data-testid='current-price'], :scope [data-test*='price'], :scope [data-testid*='price'], :scope [aria-label*='$']"
            price_el = card.locator(price_selector).first
            if await price_el.count() > 0:
                price_text = await price_el.inner_text()

            if title_text and href and len(title_text) > 5:  # Ensure meaningful title
                products.append({
                    "title": title_text.strip(),
                    "price": price_text.strip() if price_text else "N/A",
                    "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
                    "category": category_name,
                    "scraped_at": datetime.utcnow().isoformat()
                })
                extracted_count += 1
        except Exception as e:
            Actor.log.warning(f"Error extracting product: {e}")
            continue

    Actor.log.info(f"{category_name}: Successfully extracted {extracted_count} products")
    return products


async def main():
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}
        test_mode = actor_input.get("testMode", True)
        max_categories = actor_input.get("maxCategories", 3 if test_mode else 100)

        Actor.log.info("=" * 60)
        Actor.log.info("Lowe's Scraper - WORKING VERSION")
        Actor.log.info("=" * 60)

        # Test categories
        categories = [
            {"name": "Paint Cleaners", "url": "https://www.lowes.com/pl/paint-cleaners-chemicals-additives/2521972965619"},
            {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
            {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
        ][:max_categories]

        async with async_playwright() as p:
            # CRITICAL: Use Chrome, not Chromium!
            # NO playwright-stealth - it's a red flag!
            profile_dir = Path(".playwright-profiles/lowes-scraper")
            profile_dir.mkdir(parents=True, exist_ok=True)

            Actor.log.info(f"Launching Chrome with persistent profile: {profile_dir}")

            context = await p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                channel='chrome',  # CRITICAL: Real Chrome
                viewport={'width': 1440, 'height': 900},
                locale='en-US',
                timezone_id='America/Los_Angeles',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-infobars',
                ]
            )

            page = context.pages[0] if context.pages else await context.new_page()

            # CRITICAL: Warmup session first!
            await warmup_session(page)

            # Set store context so products load with pricing
            # Using a default store - this should be configurable in production
            default_store_url = "https://www.lowes.com/store/FL-NorthMiamiBeach/0552"
            await set_store_context(page, default_store_url)

            # Scrape categories
            all_products = []
            for cat in categories:
                products = await scrape_category(page, cat["url"], cat["name"])
                all_products.extend(products)
                await asyncio.sleep(2)  # Delay between categories

            # Push results
            Actor.log.info(f"\nTotal products scraped: {len(all_products)}")
            if all_products:
                await Actor.push_data(all_products)
                Actor.log.info(f"SUCCESS: Pushed {len(all_products)} products to dataset")

            await context.close()

        Actor.log.info("=" * 60)
        Actor.log.info("Scraping complete!")
        Actor.log.info("=" * 60)
