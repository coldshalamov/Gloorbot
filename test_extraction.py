"""
Quick diagnostic test to see if we can extract products from a Lowe's page
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re
from typing import Optional

def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    
    # Find ALL numeric values in the text
    matches = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(text))
    if not matches:
        return None
    
    # Convert all matches to floats
    prices = []
    for match in matches:
        try:
            price = float(match.replace(",", ""))
            if price >= 1.0:
                prices.append(price)
        except (ValueError, TypeError):
            continue
    
    return max(prices) if prices else None

async def test_extraction():
    url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        print(f"🌐 Loading: {url}")
        await page.goto(url, wait_until="networkidle", timeout=45000)
        
        title = await page.title()
        print(f"📄 Page title: {title}")
        
        # Try JSON-LD extraction
        print("\n🔍 Attempting JSON-LD extraction...")
        json_ld = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)
        
        print(f"   Found {len(json_ld)} JSON-LD scripts")
        
        # Look for products in JSON-LD
        products_found = 0
        for payload in json_ld:
            if isinstance(payload, dict):
                if payload.get("@type", "").lower() == "product":
                    products_found += 1
                    offers = payload.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = parse_price(str(offers.get("price", "")))
                    print(f"   ✅ Product: {payload.get('name', 'Unknown')[:50]}")
                    print(f"      Price: ${price}")
        
        print(f"\n📊 Total products from JSON-LD: {products_found}")
        
        # Try DOM fallback
        print("\n🔍 Attempting DOM extraction...")
        raw = await page.evaluate("""
            () => {
                const items = [];
                const selectors = [
                    '[data-test="product-pod"]',
                    '[data-test="productPod"]',
                    'article',
                    'div[class*="ProductCard"]'
                ];
                
                for (const selector of selectors) {
                    const found = document.querySelectorAll(selector);
                    if (found.length > 5) {
                        console.log(`Found ${found.length} items with selector: ${selector}`);
                        found.forEach(card => {
                            try {
                                let title = card.querySelector('a[href*="/pd/"]')?.innerText?.trim();
                                let priceEl = card.querySelector('[data-test*="price"]') ||
                                            card.querySelector('span[class*="price"]');
                                let price = priceEl?.innerText?.trim();
                                let href = card.querySelector('a[href*="/pd/"]')?.getAttribute('href');
                                
                                if (title && price && href) {
                                    items.push({title: title.substring(0, 100), price, href});
                                }
                            } catch {}
                        });
                        if (items.length > 0) break;
                    }
                }
                return items;
            }
        """)
        
        print(f"   Found {len(raw)} items via DOM")
        for i, item in enumerate(raw[:3], 1):
            price = parse_price(item.get("price"))
            print(f"   {i}. {item.get('title', '')[:50]}... ${price}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_extraction())
