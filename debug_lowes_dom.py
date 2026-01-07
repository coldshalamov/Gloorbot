"""
Temporary debug script to inspect Lowe's DOM structure.
DO NOT commit this file - for debugging only.
"""
import asyncio
import json
from playwright.async_api import async_playwright
import time

async def inspect_lowes_dom():
    """Inspect Lowe's dishwasher page DOM without modifying scraper code."""
    
    result = {
        "blocked": False,
        "abck_cookie": None,
        "store_set": False,
        "counts": {},
        "sample_products": []
    }
    
    async with async_playwright() as p:
        # Use persistent Chrome profile
        profile_path = r"C:\Users\User\AppData\Local\Google\Chrome\User Data\ScraperProfile"
        
        print("🌐 Launching Chrome with persistent profile...")
        browser = await p.chromium.launch_persistent_context(
            profile_path,
            channel="chrome",
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ],
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Step 1: Warmup - visit homepage
        print("🏠 Step 1: Visiting Lowe's homepage for warmup...")
        await page.goto('https://www.lowes.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # Human-like mouse movements
        print("🖱️  Performing human-like mouse movements...")
        for _ in range(4):
            x = 300 + (time.time() % 500)
            y = 200 + (time.time() % 400)
            await page.mouse.move(x, y)
            await asyncio.sleep(0.5)
        
        # Scroll
        print("📜 Scrolling...")
        await page.evaluate("window.scrollTo(0, 800)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(3)
        
        # Check _abck cookie
        print("🍪 Checking _abck cookie for blocking...")
        cookies = await page.context.cookies()
        abck_cookie = next((c for c in cookies if c['name'] == '_abck'), None)
        
        if abck_cookie:
            result["abck_cookie"] = abck_cookie['value']
            if '~0~' in abck_cookie['value'] or '~-1~' in abck_cookie['value']:
                print(f"✅ Not blocked! _abck: {abck_cookie['value'][:50]}...")
            else:
                print(f"⚠️  Possible blocking detected! _abck: {abck_cookie['value'][:50]}...")
                result["blocked"] = True
        else:
            print("⚠️  No _abck cookie found")
        
        # Step 2: Navigate directly to dishwashers page with store parameter
        print("\n🍽️  Step 2: Navigating to dishwashers page with Auburn store...")
        # Include store in URL to set it automatically
        url = 'https://www.lowes.com/pl/dishwashers/4294857925?goToProdList=true&inStock=1&rollUpVariants=0&storeNumber=1089'
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            print("✅ Page loaded")
        except Exception as e:
            print(f"⚠️  Navigation error: {e}")
            # Try to continue anyway
        
        await asyncio.sleep(7)  # Wait for dynamic content to load
        
        # Check and apply Pickup Today filter
        print("🔍 Checking Pickup Today filter...")
        try:
            pickup_filter = page.locator('[data-selector="filter-Pickup Today"]')
            if await pickup_filter.count() > 0:
                is_checked = await pickup_filter.locator('input[type="checkbox"]').is_checked()
                if not is_checked:
                    print("📌 Applying Pickup Today filter...")
                    await pickup_filter.click()
                    await asyncio.sleep(3)
                else:
                    print("✅ Pickup Today filter already applied")
            else:
                print("ℹ️  Pickup Today filter not found")
        except Exception as e:
            print(f"⚠️  Filter check error: {e}")
        
        # Step 4: DOM Inspection
        print("\n🔬 Step 4: Inspecting DOM structure...")
        
        # Count elements
        counts = await page.evaluate("""
            () => {
                return {
                    tile_group: document.querySelectorAll('div.tile_group').length,
                    actual_price: document.querySelectorAll('[data-selector="splp-prd-act-$"]').length,
                    was_price: document.querySelectorAll('[data-selector="splp-prd-promo-was-$"]').length,
                    title: document.querySelectorAll('[data-selector="splp-prd-ttl"]').length,
                    data_tile: document.querySelectorAll('[data-tile]').length
                };
            }
        """)
        
        result["counts"] = counts
        print(f"📊 Element counts:")
        for key, value in counts.items():
            print(f"   {key}: {value}")
        
        # Extract sample products
        print("\n📦 Extracting sample products...")
        products = await page.evaluate("""
            () => {
                const samples = [];
                const tileGroups = document.querySelectorAll('div.tile_group');
                
                for (let i = 0; i < Math.min(5, tileGroups.length); i++) {
                    const group = tileGroups[i];
                    
                    const titleEl = group.querySelector('[data-selector="splp-prd-ttl"]');
                    const actualPriceEl = group.querySelector('[data-selector="splp-prd-act-$"]');
                    const wasPriceEl = group.querySelector('[data-selector="splp-prd-promo-was-$"]');
                    const linkEl = group.querySelector('a[href*="/pd/"]');
                    const dataTileEl = group.querySelector('[data-tile]');
                    
                    samples.push({
                        title: titleEl ? titleEl.textContent.trim() : null,
                        actual_price: actualPriceEl ? actualPriceEl.getAttribute('aria-label') : null,
                        was_price: wasPriceEl ? wasPriceEl.getAttribute('aria-label') : null,
                        product_link: linkEl ? linkEl.href : null,
                        data_tile: dataTileEl ? dataTileEl.getAttribute('data-tile') : null
                    });
                }
                
                return samples;
            }
        """)
        
        result["sample_products"] = products
        
        print(f"\n✅ Extracted {len(products)} sample products:")
        for i, prod in enumerate(products, 1):
            print(f"\n   Product {i}:")
            print(f"      Title: {prod['title']}")
            print(f"      Actual Price: {prod['actual_price']}")
            print(f"      Was Price: {prod['was_price']}")
            print(f"      Link: {prod['product_link']}")
            print(f"      Data-tile: {prod['data_tile']}")
        
        # Take screenshot
        screenshot_path = r"C:\Users\User\Documents\GitHub\Telomere\Gloorbot\debug_lowes_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"\n📸 Screenshot saved to: {screenshot_path}")
        
        await browser.close()
    
    # Save results to JSON
    output_path = r"C:\Users\User\Documents\GitHub\Telomere\Gloorbot\debug_lowes_dom_results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")
    return result

if __name__ == "__main__":
    asyncio.run(inspect_lowes_dom())
