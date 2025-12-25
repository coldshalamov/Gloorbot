#!/usr/bin/env python3
"""
Debug scraper - test different wait conditions and logging.
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
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        # Set up logging
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.text}"))
        page.on("response", lambda resp: print(f"[RESPONSE] {resp.url} {resp.status}"))

        url = "https://www.lowes.com/search?searchTerm=drill"
        print(f"[1] Loading: {url}")

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"[2] Response: {response.status if response else None}")

            # Wait a bit more
            await asyncio.sleep(3)

            # Check content
            print("[3] Checking content...")
            html = await page.content()
            print(f"[4] HTML length: {len(html)} bytes")
            print(f"[5] First 500 chars:\n{html[:500]}")

            # Check if we're on the right page
            url_now = page.url
            print(f"[6] Current URL: {url_now}")

            # Try to find ANY content
            body = await page.evaluate("() => document.body.innerHTML.substring(0, 1000)")
            print(f"[7] Body HTML (first 1000):\n{body}")

            # Check for Akamai challenge
            if "challenge" in html.lower() or "akamai" in html.lower():
                print("[!] Akamai challenge detected in HTML")

            if "<noscript>" in html:
                print("[!] Page requires JavaScript (has <noscript>)")

            # Try waiting for a specific element
            print("[8] Waiting for product elements...")
            try:
                await page.wait_for_selector("div", timeout=5000)
                print("[+] Found div elements")
            except Exception as e:
                print(f"[-] No divs found: {e}")

        except Exception as e:
            print(f"[ERROR] {e}")

        finally:
            await page.screenshot(path='debug_screenshot.png')
            print("[9] Screenshot saved")
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
