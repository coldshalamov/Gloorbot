"""
Deep investigation of Lowe's price structure
"""
import asyncio
from playwright.async_api import async_playwright

async def investigate_price_structure():
    """Investigate the actual price structure on Lowe's to understand the selectors"""
    
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
        await page.goto('https://www.lowes.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # Go to dishwashers
        url = 'https://www.lowes.com/pl/dishwashers/4294857925?goToProdList=true&inStock=1&rollUpVariants=0&storeNumber=1089'
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(7)
        
        # Deep investigation of first product's price structure
        print("\n" + "="*80)
        print("INVESTIGATING PRICE STRUCTURE")
        print("="*80 + "\n")
        
        result = await page.evaluate("""
            () => {
                const tile = document.querySelector('div.tile_group');
                if (!tile) return { error: "No tile_group found" };
                
                // Get ALL elements that might contain prices
                const allPriceElements = [];
                
                // Method 1: data-selector attributes
                const selectors = [
                    '[data-selector="splp-prd-act-$"]',
                    '[data-selector="splp-prd-promo-was-$"]',
                    '[data-selector="splp-prd-promo-$"]',
                    '[data-selector*="price"]',
                    '[data-selector*="prd"]'
                ];
                
                for (const sel of selectors) {
                    const els = tile.querySelectorAll(sel);
                    els.forEach(el => {
                        allPriceElements.push({
                            selector: sel,
                            tagName: el.tagName,
                            className: el.className,
                            dataSelector: el.getAttribute('data-selector'),
                            ariaLabel: el.getAttribute('aria-label'),
                            textContent: el.textContent.trim(),
                            innerHTML: el.innerHTML.substring(0, 100)
                        });
                    });
                }
                
                // Method 2: Look for any element with $ in text
                const allElements = tile.querySelectorAll('*');
                const dollarElements = [];
                allElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text.includes('$') && text.length < 50 && !text.includes('Save')) {
                        // Check if it's a direct text node (not inherited from children)
                        let hasDirectDollar = false;
                        for (const node of el.childNodes) {
                            if (node.nodeType === 3 && node.textContent.includes('$')) {
                                hasDirectDollar = true;
                                break;
                            }
                        }
                        if (hasDirectDollar || el.children.length === 0) {
                            dollarElements.push({
                                tagName: el.tagName,
                                className: el.className,
                                dataSelector: el.getAttribute('data-selector'),
                                ariaLabel: el.getAttribute('aria-label'),
                                textContent: text
                            });
                        }
                    }
                });
                
                return {
                    priceElements: allPriceElements,
                    dollarElements: dollarElements.slice(0, 10) // Limit to first 10
                };
            }
        """)
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
        else:
            print("PRICE ELEMENTS (by data-selector):")
            print("-" * 80)
            for i, el in enumerate(result['priceElements'], 1):
                print(f"\n{i}. Selector: {el['selector']}")
                print(f"   Tag: {el['tagName']}, Class: {el['className']}")
                print(f"   data-selector: {el['dataSelector']}")
                print(f"   aria-label: {el['ariaLabel']}")
                print(f"   textContent: {el['textContent']}")
            
            print("\n\n" + "="*80)
            print("ALL ELEMENTS WITH $ (first 10):")
            print("-" * 80)
            for i, el in enumerate(result['dollarElements'], 1):
                print(f"\n{i}. Tag: {el['tagName']}, Class: {el['className']}")
                print(f"   data-selector: {el['dataSelector']}")
                print(f"   aria-label: {el['ariaLabel']}")
                print(f"   Text: {el['textContent']}")
        
        print("\n" + "="*80)
        print("\nPress Enter to close browser...")
        input()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_price_structure())
