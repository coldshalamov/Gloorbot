
import asyncio
import time
import random
import re
from playwright.async_api import async_playwright, Page, Route

# Import the original scraper logic
# We assume scraper_original.py is in the same folder
import scraper_original

# ==============================================================================
# OPTIMIZATION LOGIC (Resource Blocking)
# ==============================================================================

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
# Combined list of blocked patterns for efficiency
BLOCKED_URL_PATTERNS = [
    r"google-analytics\.com", r"googletagmanager\.com", r"facebook\.net",
    r"doubleclick\.net", r"analytics", r"tracking", r"beacon", r"pixel",
    r"ads\.", r"ad\.", r"adservice", r"pagead",
    r"youtube\.com", r"vimeo\.com", r"brightcove",
    r"twitter\.com/widgets", r"pinterest\.com", r"linkedin\.com",
    r"hotjar\.com", r"clarity\.ms", r"newrelic\.com", r"sentry\.io",
    r"segment\.com", r"optimizely\.com", r"fullstory\.com", r"heap\.io",
    r"amplitude\.com", r"mixpanel\.com", r"intercom\.io", r"drift\.com",
    r"zendesk\.com", r"livechat\.com", r"tawk\.to",
    r"\.woff2?(\?|$)", r"\.ttf(\?|$)", r"\.eot(\?|$)",
]

# Essential patterns to NEVER block
NEVER_BLOCK_PATTERNS = [
    r"/_sec/", r"/akam/", r"akamai", r"lowes\.com",
    r"cloudfront", r"/pl/", r"/pd/", r"/c/",
]

async def setup_optimized_interception(page: Page) -> None:
    """Injects aggressive resource blocking to speed up load times."""
    async def handle_route(route: Route):
        request = route.request
        url = request.url.lower()
        resource_type = request.resource_type

        # Allow essentials
        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.continue_()
                return

        # Block types
        if resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return

        # Block patterns
        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", handle_route)

# ==============================================================================
# TEST RUNNER
# ==============================================================================

async def run_test():
    target_url = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"
    store_info = {"name": "Rainier", "store_id": "0004"}
    
    print("\nStarting Optimization Benchmark...")
    print(f"Target: {target_url}\n")
    
    results = []

    async with async_playwright() as p:
        # Define scenarios
        scenarios = [
            {"name": "Chromium (Original)", "channel": None, "optimized": False},
            {"name": "Chromium (Optimized)", "channel": None, "optimized": True},
            {"name": "Chrome (Original)", "channel": "chrome", "optimized": False},
            {"name": "Chrome (Optimized)", "channel": "chrome", "optimized": True},
        ]

        for sc in scenarios:
            name = sc["name"]
            channel = sc["channel"]
            is_opt = sc["optimized"]
            
            print(f"\n[{name}] Launching...")
            
            launch_opts = {
                "headless": False,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                ]
            }
            if channel:
                launch_opts["channel"] = channel

            try:
                browser = await p.chromium.launch(**launch_opts)
            except Exception as e:
                print(f"  Skipping {name}: Could not launch browser ({e})")
                continue

            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()

            if is_opt:
                await setup_optimized_interception(page)

            print(f"  Running scraper...")
            start_time = time.time()
            status = "UNKNOWN"
            product_count = 0
            
            try:
                 # Pre-set store cookie
                await context.add_cookies([{
                    "name": "sn", "value": "2420", "domain": ".lowes.com", "path": "/"
                }])
                
                # Run the actual scraper function
                # We expect it might raise "Blocked by anti-bot" exception
                products = await asyncio.wait_for(
                    scraper_original.scrape_category_page(page, target_url, store_info, 1),
                    timeout=60.0
                )
                product_count = len(products)
                status = "SUCCESS" if product_count > 0 else "EMPTY"
            
            except asyncio.TimeoutError:
                status = "TIMEOUT"
            except Exception as e:
                if "Blocked" in str(e) or "Access Denied" in str(e):
                    status = "BLOCKED"
                else:
                    status = f"ERROR: {str(e)[:50]}"
            
            duration = time.time() - start_time
            print(f"  Result: {status} | Time: {duration:.2f}s | Products: {product_count}")
            
            results.append({
                "scenario": name,
                "status": status,
                "time": duration,
                "products": product_count
            })
            
            await context.close()
            await browser.close()

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print(f"{'SCENARIO':<25} | {'STATUS':<10} | {'TIME':<8} | {'PRODS':<5}")
    print("-" * 60)
    for r in results:
        print(f"{r['scenario']:<25} | {r['status']:<10} | {r['time']:<6.2f}s  | {r['products']:<5}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_test())
