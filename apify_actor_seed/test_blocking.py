"""
Quick test to verify Apify actor works locally and doesn't get blocked by Akamai
"""
import asyncio
import sys
import os
from playwright.async_api import async_playwright

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_blocking():
    """Test if we can access Lowes without getting blocked"""
    print("🧪 Testing Lowe's access with anti-fingerprinting...")

    async with async_playwright() as p:
        # Launch with anti-bot settings
        browser = await p.chromium.launch(
            headless=False,  # CRITICAL: Akamai blocks headless
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create context with randomized fingerprint
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles'
        )

        # Inject anti-fingerprinting scripts
        await context.add_init_script("""
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Randomize canvas fingerprint
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                const context = this.getContext('2d');
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = imageData.data[i] + Math.random() * 0.1;
                }
                context.putImageData(imageData, 0, 0);
                return originalToDataURL.apply(this, arguments);
            };
        """)

        page = await context.new_page()

        try:
            print("📡 Navigating to Lowe's homepage...")
            response = await page.goto('https://www.lowes.com/', wait_until='domcontentloaded', timeout=30000)

            print(f"✅ Response status: {response.status}")

            # Wait a bit for any blocking to kick in
            await asyncio.sleep(3)

            # Check for blocking indicators
            content = await page.content()
            title = await page.title()

            print(f"📄 Page title: {title}")

            # Check for Akamai block page
            if 'Access Denied' in content or 'blocked' in content.lower():
                print("❌ BLOCKED: Detected Akamai block page")
                await page.screenshot(path='apify_actor_seed/blocked_screenshot.png')
                print("📸 Screenshot saved to blocked_screenshot.png")
                return False

            # Check if we can see product elements
            await page.wait_for_selector('body', timeout=5000)

            # Look for typical Lowe's elements
            has_header = await page.locator('header').count() > 0
            has_nav = await page.locator('nav').count() > 0

            if has_header and has_nav:
                print("✅ SUCCESS: Page loaded with normal structure")
                await page.screenshot(path='apify_actor_seed/success_screenshot.png')
                print("📸 Screenshot saved to success_screenshot.png")
                return True
            else:
                print("⚠️  WARNING: Page loaded but structure looks unusual")
                await page.screenshot(path='apify_actor_seed/unusual_screenshot.png')
                return False

        except Exception as e:
            print(f"❌ ERROR: {e}")
            await page.screenshot(path='apify_actor_seed/error_screenshot.png')
            return False
        finally:
            await browser.close()

if __name__ == '__main__':
    result = asyncio.run(test_blocking())
    sys.exit(0 if result else 1)
