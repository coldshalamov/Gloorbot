#!/usr/bin/env python3
"""
Inspect actual Lowe's page structure - don't extract, just examine.
"""

import sys
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        # Apply stealth correctly (await it)
        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        print("[1] Loading Lowe's clearance page...")
        response = await page.goto(
            "https://www.lowes.com/search?searchTerm=clearance",
            wait_until="networkidle",
            timeout=45000
        )

        print(f"[2] Status: {response.status}")
        title = await page.title()
        print(f"[3] Title: {title}")

        # Check what HTML structure exists
        print("\n[4] Inspecting page structure...")

        # Try to find ANY product containers
        structure = await page.evaluate("""
            () => {
                const debug = {};

                // Check for common Lowe's elements
                debug['[data-test="product-pod"]'] = document.querySelectorAll('[data-test="product-pod"]').length;
                debug['article'] = document.querySelectorAll('article').length;
                debug['div.ProductCard'] = document.querySelectorAll('div[class*="ProductCard"]').length;
                debug['div.product-'] = document.querySelectorAll('div[class*="product-"]').length;
                debug['[data-testid*="product"]'] = document.querySelectorAll('[data-testid*="product"]').length;
                debug['h2'] = document.querySelectorAll('h2').length;
                debug['a[href*="/pd/"]'] = document.querySelectorAll('a[href*="/pd/"]').length;

                // Find ANY elements with price in them
                const priceElements = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.innerText && el.innerText.includes('$') && el.innerText.length < 100) {
                        priceElements.push({
                            tag: el.tagName,
                            class: el.className,
                            text: el.innerText.substring(0, 50)
                        });
                    }
                });

                debug['price_elements_found'] = priceElements.length;
                if (priceElements.length > 0) {
                    debug['first_price_element'] = priceElements[0];
                }

                return debug;
            }
        """)

        print("\nElements found:")
        for key, val in structure.items():
            print(f"  {key}: {val}")

        # Get page HTML snippet
        print("\n[5] First 2000 chars of page body:")
        body_snippet = await page.evaluate("""
            () => document.body.innerText.substring(0, 2000)
        """)
        print(body_snippet)

        # Screenshot for visual inspection
        print("\n[6] Taking screenshot...")
        await page.screenshot(path='inspection_screenshot.png')
        print("Screenshot saved: inspection_screenshot.png")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
