"""
Final verification script - Extract products and show raw price data
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def verify_prices():
    """Verify that price extraction is correct by showing raw DOM data"""
    
    async with async_playwright() as p:
        profile_path = r"C:\Users\User\AppData\Local\Google\Chrome\User Data\ScraperProfile"
        
        print("🌐 Launching browser...")
        browser = await p.chromium.launch_persistent_context(
            profile_path,
            channel="chrome",
            headless=False,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Warmup
        print("🏠 Warmup...")
        await page.goto('https://www.lowes.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # Go to dishwashers
        print("🍽️  Loading dishwashers page...")
        url = 'https://www.lowes.com/pl/dishwashers/4294857925?goToProdList=true&inStock=1&rollUpVariants=0&storeNumber=1089'
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(7)
        
        # Extract first 3 products with ALL price information
        print("\n📦 Extracting products with detailed price info...\n")
        
        products = await page.evaluate("""
            () => {
                const results = [];
                const tiles = document.querySelectorAll('div.tile_group');
                
                for (let i = 0; i < Math.min(3, tiles.length); i++) {
                    const tile = tiles[i];
                    
                    // Get title
                    const titleEl = tile.querySelector('[data-selector="splp-prd-ttl"]');
                    const title = titleEl ? titleEl.textContent.trim() : 'NO TITLE';
                    
                    // Get ALL price elements and their data
                    const actualPriceEl = tile.querySelector('[data-selector="splp-prd-act-$"]');
                    const wasPriceEl = tile.querySelector('[data-selector="splp-prd-promo-was-$"]');
                    
                    const actualPriceAriaLabel = actualPriceEl ? actualPriceEl.getAttribute('aria-label') : null;
                    const actualPriceText = actualPriceEl ? actualPriceEl.textContent.trim() : null;
                    
                    const wasPriceAriaLabel = wasPriceEl ? wasPriceEl.getAttribute('aria-label') : null;
                    const wasPriceText = wasPriceEl ? wasPriceEl.textContent.trim() : null;
                    
                    // Get link
                    const linkEl = tile.querySelector('a[href*="/pd/"]');
                    const link = linkEl ? linkEl.href : 'NO LINK';
                    
                    results.push({
                        title: title.substring(0, 60),
                        actual_price_aria: actualPriceAriaLabel,
                        actual_price_text: actualPriceText,
                        was_price_aria: wasPriceAriaLabel,
                        was_price_text: wasPriceText,
                        link: link.substring(0, 80)
                    });
                }
                
                return results;
            }
        """)
        
        for i, p in enumerate(products, 1):
            print(f"{'='*80}")
            print(f"Product {i}:")
            print(f"  Title: {p['title']}")
            print(f"  Link: {p['link']}")
            print(f"\n  ACTUAL PRICE:")
            print(f"    aria-label: {p['actual_price_aria']}")
            print(f"    textContent: {p['actual_price_text']}")
            print(f"\n  WAS PRICE:")
            print(f"    aria-label: {p['was_price_aria']}")
            print(f"    textContent: {p['was_price_text']}")
            print()
        
        print(f"{'='*80}\n")
        
        # Save results
        output_path = r"C:\Users\User\Documents\GitHub\Telomere\Gloorbot\price_verification.json"
        with open(output_path, 'w') as f:
            json.dump(products, f, indent=2)
        
        print(f"💾 Results saved to: {output_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_prices())
