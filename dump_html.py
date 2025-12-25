#!/usr/bin/env python3
"""
Dump actual Lowe's HTML to file so we can inspect it.
"""

import asyncio
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        url = "https://www.lowes.com/search?searchTerm=drill"
        print(f"Loading: {url}")

        response = await page.goto(url, wait_until="networkidle", timeout=45000)
        print(f"Status: {response.status}")

        # Wait for content
        await asyncio.sleep(2)

        # Get HTML
        html = await page.content()
        print(f"HTML length: {len(html)}")

        # Save to file
        with open('lowes_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved to lowes_page.html")

        # Also get the body innerHTML
        body = await page.evaluate("() => document.body.innerHTML")
        with open('lowes_body.html', 'w', encoding='utf-8') as f:
            f.write(body)
        print("Saved to lowes_body.html")

        # Find any elements with "product" in class
        classes_with_product = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('[class*="product" i], [class*="item" i]');
                const classes = new Set();
                elements.forEach(el => {
                    if (el.className) {
                        classes.add(el.className);
                    }
                });
                return Array.from(classes).slice(0, 50);
            }
        """)

        print(f"\nClasses containing 'product' or 'item':")
        for cls in classes_with_product:
            print(f"  {cls[:100]}")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
