"""
Coverage Validation Script - Extract all departments from Lowe's live site
Compares against LowesMap.txt to find missing or redundant URLs
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
try:
    from playwright_stealth import Stealth
    stealth = Stealth()
except ImportError:
    stealth = None

async def extract_departments():
    """Extract all department URLs from Lowe's Shop All Departments."""
    departments = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        if stealth:
            await stealth.apply_stealth_async(page)
        
        print("Navigating to Lowe's homepage...")
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        print("Extracting department links...")
        
        # Try multiple strategies to find department links
        strategies = [
            # Strategy 1: Main navigation mega menu
            'a[href*="/pl/"]',
            # Strategy 2: Footer links
            'footer a[href*="/pl/"]',
            # Strategy 3: Shop by department section
            '[data-selector*="department"] a[href*="/pl/"]',
        ]
        
        all_links = set()
        for selector in strategies:
            try:
                links = await page.query_selector_all(selector)
                for link in links:
                    href = await link.get_attribute('href')
                    if href and '/pl/' in href:
                        # Normalize URL
                        if href.startswith('/'):
                            href = f"https://www.lowes.com{href}"
                        # Remove query params for comparison
                        base_url = href.split('?')[0].rstrip('/')
                        all_links.add(base_url)
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
        
        # Also try clicking "Shop All Departments" if it exists
        try:
            shop_all = await page.query_selector('button:has-text("Shop"), a:has-text("Shop All")')
            if shop_all:
                print("Found 'Shop All' button, clicking...")
                await shop_all.click()
                await asyncio.sleep(2)
                
                # Extract from mega menu
                mega_links = await page.query_selector_all('a[href*="/pl/"]')
                for link in mega_links:
                    href = await link.get_attribute('href')
                    if href and '/pl/' in href:
                        if href.startswith('/'):
                            href = f"https://www.lowes.com{href}"
                        base_url = href.split('?')[0].rstrip('/')
                        all_links.add(base_url)
        except Exception as e:
            print(f"Could not click Shop All: {e}")
        
        await browser.close()
        
        departments = sorted(list(all_links))
        print(f"\nExtracted {len(departments)} unique department URLs from live site")
        
        return departments

def load_lowesmap():
    """Load URLs from LowesMap.txt."""
    map_path = Path("LowesMap.txt")
    if not map_path.exists():
        print("ERROR: LowesMap.txt not found!")
        return []
    
    urls = []
    with open(map_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '/pl/' in line:
                base_url = line.split('?')[0].rstrip('/')
                urls.append(base_url)
    
    return sorted(list(set(urls)))

def compare_coverage(live_urls, map_urls):
    """Compare live site URLs vs LowesMap.txt."""
    live_set = set(live_urls)
    map_set = set(map_urls)
    
    missing = live_set - map_set
    extra = map_set - live_set
    common = live_set & map_set
    
    report = {
        "summary": {
            "live_site_urls": len(live_urls),
            "lowesmap_urls": len(map_urls),
            "common_urls": len(common),
            "missing_from_map": len(missing),
            "extra_in_map": len(extra),
            "coverage_percentage": round(len(common) / len(live_set) * 100, 2) if live_set else 0
        },
        "missing_urls": sorted(list(missing)),
        "extra_urls": sorted(list(extra)),
    }
    
    return report

async def main():
    print("="*60)
    print("LOWE'S COVERAGE VALIDATION")
    print("="*60)
    
    # Step 1: Extract from live site
    print("\n[1/3] Extracting departments from live site...")
    live_urls = await extract_departments()
    
    # Step 2: Load LowesMap.txt
    print("\n[2/3] Loading LowesMap.txt...")
    map_urls = load_lowesmap()
    print(f"Found {len(map_urls)} URLs in LowesMap.txt")
    
    # Step 3: Compare
    print("\n[3/3] Comparing coverage...")
    report = compare_coverage(live_urls, map_urls)
    
    # Save report
    with open("coverage_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("COVERAGE REPORT")
    print("="*60)
    print(f"Live Site URLs:        {report['summary']['live_site_urls']}")
    print(f"LowesMap.txt URLs:     {report['summary']['lowesmap_urls']}")
    print(f"Common URLs:           {report['summary']['common_urls']}")
    print(f"Missing from Map:      {report['summary']['missing_from_map']}")
    print(f"Extra in Map:          {report['summary']['extra_in_map']}")
    print(f"Coverage:              {report['summary']['coverage_percentage']}%")
    
    if report['summary']['missing_from_map'] > 0:
        print(f"\n⚠️  WARNING: {report['summary']['missing_from_map']} URLs found on live site but missing from LowesMap.txt")
        print("First 10 missing URLs:")
        for url in report['missing_urls'][:10]:
            print(f"  - {url}")
    
    if report['summary']['extra_in_map'] > 0:
        print(f"\n💡 INFO: {report['summary']['extra_in_map']} URLs in LowesMap.txt not found on live site")
        print("These may be valid deep links or outdated URLs")
    
    print(f"\n✅ Full report saved to: coverage_report.json")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
