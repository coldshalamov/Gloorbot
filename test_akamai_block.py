"""
Check if we're being blocked by Akamai
"""
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def check_blocking():
    url = "https://www.lowes.com"
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        print(f"🌐 Loading: {url}")
        response = await page.goto(url, wait_until="networkidle", timeout=45000)
        
        print(f"📡 HTTP Status: {response.status}")
        
        title = await page.title()
        print(f"📄 Page title: '{title}'")
        
        # Check for Akamai block
        if "Access Denied" in title or "Access Denied" in await page.content():
            print("❌ BLOCKED by Akamai!")
        elif not title or len(title) < 3:
            print("⚠️  Empty title - possible block or loading issue")
        else:
            print("✅ Page loaded successfully!")
        
        # Check cookies
        cookies = await context.cookies()
        abck_cookie = next((c for c in cookies if c['name'] == '_abck'), None)
        if abck_cookie:
            print(f"🍪 _abck cookie: {abck_cookie['value'][:50]}...")
            if '~0~' in abck_cookie['value']:
                print("   ✅ Good Akamai signal (~0~ present)")
            else:
                print("   ⚠️  May need warmup (no ~0~ in cookie)")
        else:
            print("🍪 No _abck cookie found")
        
        # Wait a bit for user to see the page
        print("\n⏸️  Pausing for 5 seconds to inspect page...")
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_blocking())
