
import asyncio
import os
import re
import time
import random
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Fix paths
BASE_DIR = Path(__file__).parent.absolute()
sys.path.append(str(BASE_DIR))
original_path = BASE_DIR / "scraper_original.py"
optimized_path = BASE_DIR / "scraper_optimized.py"

# Import original scraper (after modifying sys.path)
import scraper_original

# Create optimized scraper dynamically
with open(original_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add resource blocking logic
imports = "from playwright.async_api import async_playwright, Page, Locator, Route"
content = content.replace("from playwright.async_api import async_playwright, Page, Locator", imports)

blocking_code = """
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
BLOCKED_URL_PATTERNS = [
    r"google-analytics\\.com", r"googletagmanager\\.com", r"facebook\\.net",
    r"doubleclick\\.net", r"analytics", r"tracking", r"beacon", r"pixel",
    r"ads\\.", r"ad\\.", r"adservice", r"pagead",
    r"youtube\\.com", r"vimeo\\.com", r"brightcove",
    r"twitter\\.com/widgets", r"pinterest\\.com", r"linkedin\\.com",
    r"hotjar\\.com", r"clarity\\.ms", r"newrelic\\.com", r"sentry\\.io",
]
NEVER_BLOCK_PATTERNS = [
    r"/_sec/", r"/akam/", r"akamai", r"lowes\\.com",
    r"cloudfront", r"/pl/", r"/pd/", r"/c/",
]

async def setup_request_interception(page: Page) -> None:
    async def handle_route(route: Route):
        request = route.request
        url = request.url.lower()
        resource_type = request.resource_type

        # NEVER block essential patterns
        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.continue_()
                return

        # Block by resource type
        if resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return

        # Block by URL pattern
        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", handle_route)
"""

# Insert blocking code
content = content.replace("# ============================================================================\n# SCRAPING", blocking_code + "\n# ============================================================================\n# SCRAPING")

# 2. Reduce delays
# Replace: await asyncio.sleep(1.5 + random.random() * 2.4)
content = content.replace("await asyncio.sleep(1.5 + random.random() * 2.4)", "await asyncio.sleep(0.5)")
# Replace: await asyncio.sleep(2.0 + random.random() * 2.55)
content = content.replace("await asyncio.sleep(2.0 + random.random() * 2.55)", "await asyncio.sleep(0.5)")
# Replace: await asyncio.sleep(1.5 + random.random() * 1.75)
content = content.replace("await asyncio.sleep(1.5 + random.random() * 1.75)", "await asyncio.sleep(0.5)")

with open(optimized_path, "w", encoding="utf-8") as f:
    f.write(content)

# Dynamic import of optimized module
import importlib.util
spec = importlib.util.spec_from_file_location("scraper_optimized", str(optimized_path))
scraper_optimized = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_optimized)

async def run_benchmark():
    # Using a known safe category URL (Lumber)
    url = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"
    store_info = {"name": "Test Store", "store_id": "0004"}
    
    print(f"Starting Benchmark using {url}...")
    
    async with async_playwright() as p:
        # Launch options
        launch_opts = {
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        browser = await p.chromium.launch(**launch_opts)
        
        # --- Run Original ---
        print("\n--- Running Original Scraper ---")
        context1 = await browser.new_context()
        page1 = await context1.new_page()
        
        print(f"Loading store page...")
        await page1.goto("https://www.lowes.com/store/WA-Seattle/0004")
        await asyncio.sleep(2)
        
        start1 = time.time()
        try:
            products1 = await scraper_original.scrape_category_page(page1, url, store_info, 1)
            dur1 = time.time() - start1
            print(f"Original: Found {len(products1)} products in {dur1:.2f}s")
        except Exception as e:
            print(f"Original Failed: {e}")
            dur1 = 999
            
        await context1.close()
        
        # --- Run Optimized ---
        print("\n--- Running Optimized Scraper ---")
        context2 = await browser.new_context()
        page2 = await context2.new_page()
        
        # Enable blocking
        await scraper_optimized.setup_request_interception(page2)
        
        print(f"Loading store page (optimized)...")
        await page2.goto("https://www.lowes.com/store/WA-Seattle/0004")
        await asyncio.sleep(2)
        
        start2 = time.time()
        try:
            products2 = await scraper_optimized.scrape_category_page(page2, url, store_info, 1)
            dur2 = time.time() - start2
            print(f"Optimized: Found {len(products2)} products in {dur2:.2f}s")
        except Exception as e:
            print(f"Optimized Failed: {e}")
            dur2 = 999
            
        await context2.close()
        await browser.close()
        
        if dur1 != 999 and dur2 != 999:
            print(f"\nImprovement: {dur1 - dur2:.2f}s ({(dur1 - dur2)/dur1*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
