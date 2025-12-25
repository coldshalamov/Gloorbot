#!/usr/bin/env python3
"""
Standalone Anti-Fingerprinting Test
Tests fingerprinting without Apify dependencies
"""

import asyncio
import random


# Anti-fingerprinting constants
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

TIMEZONES = ['America/New_York', 'America/Chicago', 'America/Los_Angeles', 'America/Denver']
LOCALES = ['en-US', 'en-GB', 'en-CA', 'en-AU']


async def inject_canvas_noise(page):
    """Inject canvas fingerprint randomization."""
    await page.add_init_script("""
        (() => {
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const noise = () => Math.random() * 0.1 - 0.05;

            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                const context = this.getContext('2d');
                if (context) {
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = imageData.data[i] + noise();
                        imageData.data[i+1] = imageData.data[i+1] + noise();
                        imageData.data[i+2] = imageData.data[i+2] + noise();
                    }
                    context.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, args);
            };
        })();
    """)


async def inject_webgl_noise(page):
    """Inject WebGL fingerprint randomization."""
    await page.add_init_script("""
        (() => {
            const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD'];
            const renderers = ['Intel Iris OpenGL Engine', 'GeForce GTX 1050', 'AMD Radeon Pro'];
            const randomVendor = vendors[Math.floor(Math.random() * vendors.length)];
            const randomRenderer = renderers[Math.floor(Math.random() * renderers.length)];

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return randomVendor;
                if (param === 37446) return randomRenderer;
                return getParameter.apply(this, arguments);
            };
        })();
    """)


async def inject_audio_noise(page):
    """Inject AudioContext fingerprint randomization."""
    await page.add_init_script("""
        (() => {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const noise = () => Math.random() * 0.0001 - 0.00005;
            const originalCreateOscillator = AudioContext.prototype.createOscillator;
            AudioContext.prototype.createOscillator = function() {
                const oscillator = originalCreateOscillator.apply(this, arguments);
                if (oscillator.frequency) {
                    const originalValue = oscillator.frequency.value;
                    Object.defineProperty(oscillator.frequency, 'value', {
                        get: () => originalValue + noise(),
                        set: (v) => {}
                    });
                }
                return oscillator;
            };
        })();
    """)


async def inject_screen_randomization(page):
    """Inject screen resolution randomization."""
    await page.add_init_script("""
        (() => {
            const offsetWidth = Math.floor(Math.random() * 20) - 10;
            const offsetHeight = Math.floor(Math.random() * 20) - 10;
            Object.defineProperty(window.screen, 'width', { get: () => 1920 + offsetWidth });
            Object.defineProperty(window.screen, 'height', { get: () => 1080 + offsetHeight });
        })();
    """)


async def test_lowes():
    """Test Lowe's access with anti-fingerprinting."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    print("\n" + "=" * 70)
    print(" ANTI-FINGERPRINTING TEST - Lowe's Akamai Bypass")
    print("=" * 70)

    async with async_playwright() as pw:
        print("\n[1/6] Launching browser (headless=False)...")
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Randomized fingerprint
        print("[2/6] Generating randomized fingerprint...")
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        selected_tz = random.choice(TIMEZONES)
        selected_locale = random.choice(LOCALES)
        selected_ua = random.choice(USER_AGENTS)

        print(f"      Viewport: {viewport_width}x{viewport_height}")
        print(f"      Timezone: {selected_tz}")
        print(f"      Locale: {selected_locale}")
        print(f"      UA: {selected_ua[:55]}...")

        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            timezone_id=selected_tz,
            locale=selected_locale,
            user_agent=selected_ua,
        )

        page = await context.new_page()

        print("\n[3/6] Applying anti-fingerprinting stack...")
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        print("      [OK] Playwright-stealth")

        await inject_canvas_noise(page)
        print("      [OK] Canvas noise injection")

        await inject_webgl_noise(page)
        print("      [OK] WebGL randomization")

        await inject_audio_noise(page)
        print("      [OK] AudioContext noise")

        await inject_screen_randomization(page)
        print("      [OK] Screen randomization")

        print("\n[4/6] Navigating to Lowe's Clearance page...")
        url = "https://www.lowes.com/pl/The-back-aisle/2021454685607"

        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            status = resp.status
            print(f"      HTTP Status: {status}")

            await asyncio.sleep(3)
            title = await page.title()
            print(f"      Page Title: {title}")

            print("\n[5/6] Checking for Akamai block...")

            # Check for block
            blocked = False
            if "Access Denied" in title:
                print("      [BLOCKED] - Title contains 'Access Denied'")
                blocked = True
            elif status == 403:
                print("      [BLOCKED] - HTTP 403 status")
                blocked = True
            else:
                content = await page.content()
                if "Access Denied" in content[:5000] or "Reference #" in content[:5000]:
                    print("      [BLOCKED] - Akamai error page detected")
                    blocked = True
                else:
                    print("      [SUCCESS] - Page loaded successfully!")

                    # Check for products
                    products = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
                    print(f"      Products visible: {len(products)}")

            print("\n[6/6] Test complete. Browser open for 15 seconds for inspection...")
            print("      Check the browser window to verify the page")
            await asyncio.sleep(15)

            await browser.close()

            print("\n" + "=" * 70)
            if not blocked:
                print(" [SUCCESS] - Anti-fingerprinting is working!")
                print(" The actor should work on Apify with residential proxies.")
            else:
                print(" [FAILED] - Still blocked by Akamai")
                print(" Additional measures may be needed.")
            print("=" * 70 + "\n")

            return not blocked

        except Exception as e:
            print(f"\n      [ERROR]: {e}")
            await asyncio.sleep(5)
            await browser.close()
            return False


if __name__ == "__main__":
    import sys
    success = asyncio.run(test_lowes())
    sys.exit(0 if success else 1)
