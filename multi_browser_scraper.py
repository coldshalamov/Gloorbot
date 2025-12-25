#!/usr/bin/env python3
"""
Working Lowe's Scraper - Based on production code that worked.
Stripped down to essentials: No pickup filter, just extract what we can.
"""

import asyncio
import sys
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

BASE_URL = "https://www.lowes.com"
STORES = {
    "0004": {"name": "Rainier", "city": "Seattle", "state": "WA"},
    "1108": {"name": "Tigard", "city": "Tigard", "state": "OR"},
}
CATEGORIES = ["Clearance", "Lumber", "Power Tools", "Paint"]

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        # Init database
        init_db()

        for store_id, store_info in STORES.items():
            store_name = f"Lowe's {store_info['name']}"

            for category in CATEGORIES:
                print(f"\n[{store_name}] {category}")

                url = f"{BASE_URL}/search?searchTerm={category.lower().replace(' ', '+')}"

                try:
                    response = await page.goto(url, wait_until="networkidle", timeout=45000)

                    if response.status >= 400:
                        print(f"  [ERROR] HTTP {response.status}")
                        continue

                    # Check for block
                    title = await page.title()
                    if "Access Denied" in title:
                        print(f"  [BLOCKED] Akamai")
                        continue

                    # Extract products
                    products = await extract_products_json_ld(page, store_id, store_name, category)

                    if not products:
                        products = await extract_products_dom(page, store_id, store_name, category)

                    if products:
                        print(f"  [OK] {len(products)} products")
                        save_products(products)
                    else:
                        print(f"  [0] No products")

                except Exception as e:
                    print(f"  [ERROR] {str(e)[:50]}")
                    continue

        await context.close()
        await browser.close()

        # Show results
        conn = sqlite3.connect('lowes_products.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products")
        count = c.fetchone()[0]
        conn.close()

        print(f"\n\nFINAL: {count} products saved to lowes_products.db")

async def extract_products_json_ld(page, store_id, store_name, category):
    """Try JSON-LD first (most reliable)."""
    try:
        scripts = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)

        products = []
        timestamp = datetime.now(timezone.utc).isoformat()

        for payload in scripts:
            items = collect_products(payload)

            for product in items:
                offers = product.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                price_str = str(offers.get("price", ""))
                if not price_str:
                    continue

                try:
                    price = float(price_str.replace("$", "").replace(",", ""))
                except:
                    continue

                price_was_str = str(offers.get("priceWas", ""))
                price_was = None
                if price_was_str:
                    try:
                        price_was = float(price_was_str.replace("$", "").replace(",", ""))
                    except:
                        pass

                image = product.get("image")
                if isinstance(image, list):
                    image = image[0] if image else None
                if image and image.startswith("//"):
                    image = f"https:{image}"

                product_url = offers.get("url") or product.get("url")
                sku = product.get("sku") or product.get("productID")

                products.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "sku": sku,
                    "title": (product.get("name") or "Unknown")[:200],
                    "category": category,
                    "price": price,
                    "price_was": price_was,
                    "pct_off": (((price_was - price) / price_was * 100) if price_was and price_was > 0 else None),
                    "availability": "In Stock",
                    "clearance": False,
                    "product_url": product_url,
                    "image_url": image,
                    "timestamp": timestamp,
                })

        return products

    except:
        return []

def collect_products(obj):
    """Recursively find product objects in JSON-LD."""
    found = []
    if isinstance(obj, dict):
        if obj.get("@type", "").lower() == "product":
            found.append(obj)
        for v in obj.values():
            found.extend(collect_products(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(collect_products(item))
    return found

async def extract_products_dom(page, store_id, store_name, category):
    """DOM fallback if JSON-LD found nothing."""
    try:
        raw = await page.evaluate("""
            () => {
                const products = [];
                const cards = document.querySelectorAll(
                    '[data-test="product-pod"], [data-test="productPod"], li:has(a[href*="/pd/"])'
                );

                cards.forEach(card => {
                    try {
                        const titleEl = card.querySelector('a[href*="/pd/"], h3, h2');
                        const priceEl = card.querySelector('[data-test*="price"], [aria-label*="$"]');
                        const linkEl = card.querySelector('a[href*="/pd/"]');
                        const imgEl = card.querySelector('img');

                        if (titleEl && priceEl) {
                            products.push({
                                title: titleEl.innerText?.trim() || '',
                                price: priceEl.innerText?.trim() || '',
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
        timestamp = datetime.now(timezone.utc).isoformat()

        for r in raw:
            price_str = r.get("price", "").replace("$", "").replace(",", "")
            try:
                price = float(price_str)
            except:
                continue

            href = r.get("href", "")
            product_url = f"{BASE_URL}{href}" if href.startswith("/") else href

            img = r.get("img", "")
            if img.startswith("//"):
                img = f"https:{img}"

            sku = None
            if product_url:
                # Extract SKU from URL
                parts = product_url.split("/")
                for part in parts:
                    if part.isdigit() and len(part) > 4:
                        sku = part
                        break

            products.append({
                "store_id": store_id,
                "store_name": store_name,
                "sku": sku,
                "title": r.get("title", "")[:200],
                "category": category,
                "price": price,
                "price_was": None,
                "pct_off": None,
                "availability": "In Stock",
                "clearance": False,
                "product_url": product_url,
                "image_url": img if img else None,
                "timestamp": timestamp,
            })

        return products

    except:
        return []

def init_db():
    """Create database schema."""
    conn = sqlite3.connect('lowes_products.db')
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            store_id TEXT,
            store_name TEXT,
            sku TEXT,
            title TEXT,
            category TEXT,
            price REAL,
            price_was REAL,
            pct_off REAL,
            availability TEXT,
            clearance INTEGER,
            product_url TEXT,
            image_url TEXT,
            UNIQUE(store_id, sku)
        )
    """)

    conn.commit()
    conn.close()

def save_products(products):
    """Save products to database."""
    conn = sqlite3.connect('lowes_products.db')
    c = conn.cursor()

    for p in products:
        try:
            c.execute("""
                INSERT OR REPLACE INTO products
                (timestamp, store_id, store_name, sku, title, category, price, price_was, pct_off,
                 availability, clearance, product_url, image_url)
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
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
