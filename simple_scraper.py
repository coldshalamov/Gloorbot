#!/usr/bin/env python3
"""
Minimal Lowe's scraper - Just test if we can get products.
No parallelism, no complex logic. Just: open browser, scrape, save.
"""

import sys
import asyncio
import sqlite3
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as pw:
        # Launch browser
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        # Apply stealth
        stealth = Stealth()
        stealth.apply_stealth_async(context)

        page = await context.new_page()

        # Try to access Lowe's
        print("[1] Opening Lowe's Clearance page...")
        try:
            response = await page.goto(
                "https://www.lowes.com/search?searchTerm=clearance",
                wait_until="networkidle",
                timeout=45000
            )

            print(f"[2] Status: {response.status if response else 'NO RESPONSE'}")

            # Check title
            title = await page.title()
            print(f"[3] Page title: {title}")

            # Check for block
            if "Access Denied" in title or "Unauthorized" in title:
                print("[!] BLOCKED - Akamai detected scraper")
                return

            # Try to extract products
            print("[4] Attempting to extract products...")
            products = await page.evaluate("""
                () => {
                    const items = [];
                    const selectors = [
                        '[data-test="product-pod"]',
                        'article',
                        'div[class*="ProductCard"]',
                    ];

                    for (const selector of selectors) {
                        const found = document.querySelectorAll(selector);
                        console.log(`Selector ${selector}: ${found.length} matches`);

                        if (found.length > 3) {
                            found.slice(0, 5).forEach(card => {
                                try {
                                    const title = card.innerText?.split('\\n')[0] || '';
                                    const price = card.innerText?.match(/\\$[0-9.]+/)?.[0] || '';
                                    const link = card.querySelector('a[href*="/pd/"]')?.href || '';

                                    if (title && title.length > 3 && (price || link)) {
                                        items.push({title: title.substring(0, 100), price, link});
                                    }
                                } catch (e) {}
                            });

                            if (items.length > 0) {
                                console.log(`Found ${items.length} items with selector ${selector}`);
                                break;
                            }
                        }
                    }
                    return items;
                }
            """)

            print(f"[5] Extracted {len(products)} products")

            if len(products) > 0:
                print("\n[SUCCESS] Got products:")
                for i, p in enumerate(products[:3], 1):
                    print(f"  {i}. {p['title'][:60]}")
                    print(f"     Price: {p['price']}, Link: {p['link'][:50]}...")

                # Save to database
                print("\n[6] Saving to database...")
                save_to_db(products)
                print("[SUCCESS] Database saved")

            else:
                print("[!] No products extracted")
                print("[!] Selectors may not match current Lowe's HTML")

        except Exception as e:
            print(f"[ERROR] {str(e)}")

        finally:
            await context.close()
            await browser.close()

def save_to_db(products):
    """Save products to SQLite."""
    conn = sqlite3.connect('simple_test.db')
    c = conn.cursor()

    # Create table
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            title TEXT,
            price TEXT,
            link TEXT,
            timestamp TEXT
        )
    """)

    # Insert
    now = datetime.now(timezone.utc).isoformat()
    for p in products:
        c.execute(
            "INSERT INTO products (title, price, link, timestamp) VALUES (?, ?, ?, ?)",
            (p.get('title'), p.get('price'), p.get('link'), now)
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
