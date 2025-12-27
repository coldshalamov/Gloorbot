"""
URL Quality Validator - Test sample URLs from LowesMap.txt to verify they contain products
"""
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

async def test_url_quality(url, browser):
    """Test if a URL contains product listings."""
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    page = await context.new_page()
    
    try:
        print(f"\nTesting: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        # Check for product listings
        products = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
        product_count = len(products)
        
        # Check for "Pickup Today" filter
        pickup_filter = await page.query_selector('label:has-text("Get It Today"), label:has-text("Pickup Today")')
        has_pickup_filter = pickup_filter is not None
        
        # Check for pagination
        pagination = await page.query_selector('[data-selector="pagination"], nav[aria-label*="pagination"]')
        has_pagination = pagination is not None
        
        # Check title
        title = await page.title()
        
        result = {
            "url": url,
            "product_count": product_count,
            "has_pickup_filter": has_pickup_filter,
            "has_pagination": has_pagination,
            "title": title,
            "status": "VALID" if product_count > 0 else "NO_PRODUCTS"
        }
        
        print(f"  Products: {product_count}")
        print(f"  Pickup Filter: {has_pickup_filter}")
        print(f"  Pagination: {has_pagination}")
        print(f"  Status: {result['status']}")
        
        return result
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            "url": url,
            "error": str(e),
            "status": "ERROR"
        }
    finally:
        await context.close()

async def main():
    # Load URLs from LowesMap.txt
    map_path = Path("LowesMap.txt")
    urls = []
    with open(map_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '/pl/' in line:
                urls.append(line)
    
    # Sample 20 random URLs for testing
    sample_urls = random.sample(urls, min(20, len(urls)))
    
    print("="*60)
    print(f"URL QUALITY VALIDATION")
    print(f"Testing {len(sample_urls)} random URLs from LowesMap.txt")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        results = []
        for url in sample_urls:
            result = await test_url_quality(url, browser)
            results.append(result)
            await asyncio.sleep(1)  # Rate limiting
        
        await browser.close()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    valid = [r for r in results if r.get("status") == "VALID"]
    no_products = [r for r in results if r.get("status") == "NO_PRODUCTS"]
    errors = [r for r in results if r.get("status") == "ERROR"]
    
    print(f"Valid URLs (with products):  {len(valid)}/{len(results)}")
    print(f"Empty URLs (no products):    {len(no_products)}/{len(results)}")
    print(f"Error URLs:                  {len(errors)}/{len(results)}")
    
    if no_products:
        print("\n⚠️  URLs with no products:")
        for r in no_products:
            print(f"  - {r['url']}")
    
    if errors:
        print("\n❌ URLs with errors:")
        for r in errors:
            print(f"  - {r['url']}: {r.get('error', 'Unknown')}")
    
    # Calculate average products per page
    avg_products = sum(r.get("product_count", 0) for r in valid) / len(valid) if valid else 0
    print(f"\nAverage products per page: {avg_products:.1f}")
    
    # Check pickup filter availability
    with_pickup = [r for r in valid if r.get("has_pickup_filter")]
    print(f"URLs with 'Pickup Today' filter: {len(with_pickup)}/{len(valid)}")
    
    print("\n✅ Validation complete!")

if __name__ == "__main__":
    asyncio.run(main())
