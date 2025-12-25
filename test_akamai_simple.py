#!/usr/bin/env python3
"""
Simple Akamai Bypass Test - No dependencies on main.py

This script tests whether Chrome + anti-fingerprinting can bypass Akamai.

Run with: python test_akamai_simple.py
"""

import asyncio
import random

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


# Fingerprint injection scripts
CANVAS_NOISE_SCRIPT = """
(() => {
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const context = this.getContext('2d');
        if (context) {
            const original = context.getImageData(0, 0, this.width, this.height);
            const noisy = context.getImageData(0, 0, this.width, this.height);
            const noise = [__R__, __G__, __B__];
            for (let i = 0; i < noisy.data.length; i += 4) {
                noisy.data[i] = Math.max(0, Math.min(255, noisy.data[i] + noise[0]));
                noisy.data[i+1] = Math.max(0, Math.min(255, noisy.data[i+1] + noise[1]));
                noisy.data[i+2] = Math.max(0, Math.min(255, noisy.data[i+2] + noise[2]));
            }
            context.putImageData(noisy, 0, 0);
            const result = originalToDataURL.apply(this, args);
            context.putImageData(original, 0, 0);
            return result;
        }
        return originalToDataURL.apply(this, args);
    };
})();
"""

WEBGL_NOISE_SCRIPT = """
(() => {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return "__VENDOR__";
        if (param === 37446) return "__RENDERER__";
        return getParameter.apply(this, arguments);
    };
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return "__VENDOR__";
            if (param === 37446) return "__RENDERER__";
            return getParameter2.apply(this, arguments);
        };
    }
})();
"""

WEBRTC_PROTECTION_SCRIPT = """
(() => {
    if (typeof RTCPeerConnection !== 'undefined') {
        const noop = () => {};
        const fakePC = function() {
            return {
                createDataChannel: noop,
                createOffer: () => Promise.resolve({}),
                setLocalDescription: () => Promise.resolve(),
                close: noop,
                addEventListener: noop,
                localDescription: null,
                signalingState: 'closed',
                iceGatheringState: 'complete',
                iceConnectionState: 'closed'
            };
        };
        window.RTCPeerConnection = fakePC;
        window.webkitRTCPeerConnection = fakePC;
    }
})();
"""

PERMISSIONS_SCRIPT = """
(() => {
    navigator.permissions.query = async (params) => {
        const name = params.name || params;
        return { state: 'prompt', onchange: null, addEventListener: () => {} };
    };
})();
"""


async def apply_fingerprint_protection(page):
    """Apply all fingerprint protection scripts."""
    # Canvas noise
    r, g, b = random.randint(-3, 3), random.randint(-3, 3), random.randint(-3, 3)
    canvas_script = CANVAS_NOISE_SCRIPT.replace("__R__", str(r)).replace("__G__", str(g)).replace("__B__", str(b))
    await page.add_init_script(canvas_script)

    # WebGL randomization
    vendors = ["Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)"]
    renderers = [
        "ANGLE (NVIDIA GeForce GTX 1080 Direct3D11)",
        "ANGLE (Intel HD Graphics 630 Direct3D11)",
        "ANGLE (AMD Radeon RX 580 Direct3D11)",
    ]
    webgl_script = WEBGL_NOISE_SCRIPT.replace("__VENDOR__", random.choice(vendors)).replace("__RENDERER__", random.choice(renderers))
    await page.add_init_script(webgl_script)

    # WebRTC protection
    await page.add_init_script(WEBRTC_PROTECTION_SCRIPT)

    # Permissions
    await page.add_init_script(PERMISSIONS_SCRIPT)


async def test_akamai_bypass():
    """Test if we can access Lowe's without getting blocked."""

    print("=" * 60)
    print("AKAMAI BYPASS TEST (Simple Version)")
    print("=" * 60)

    # Test URL - Paint category with On Sale filter
    test_url = "https://www.lowes.com/pl/Paint/4294644082"

    print(f"\nTarget URL: {test_url}")
    print("Browser: Chrome (not Chromium)")
    print("\nLaunching browser...")

    async with async_playwright() as p:
        # CRITICAL: Use real Chrome, not Chromium!
        browser = await p.chromium.launch(
            headless=False,  # CRITICAL: Akamai blocks headless
            channel="chrome",  # CRITICAL: Use real Chrome
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1440,900",
            ],
        )

        # Create context with realistic settings
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/Los_Angeles",
            color_scheme="light",
        )

        page = await context.new_page()

        # Apply stealth
        print("Applying playwright-stealth...")
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        # Apply fingerprint protection
        print("Applying fingerprint protection...")
        await apply_fingerprint_protection(page)

        # Navigate to Lowe's
        print(f"\nNavigating to {test_url}...")
        try:
            response = await page.goto(test_url, timeout=60000, wait_until="domcontentloaded")

            # Wait a moment for page to render
            await asyncio.sleep(2)

            # Check for blocks
            title = await page.title()
            url = page.url

            print(f"\nResponse status: {response.status if response else 'N/A'}")
            print(f"Page title: {title}")
            print(f"Final URL: {url}")

            # Check for Akamai block indicators
            blocked = False
            block_reasons = []

            if response and response.status == 403:
                blocked = True
                block_reasons.append("HTTP 403 Forbidden")

            if "access denied" in title.lower():
                blocked = True
                block_reasons.append("'Access Denied' in page title")

            if "edgesuite" in url.lower() or "akamai" in url.lower():
                blocked = True
                block_reasons.append("Redirected to Akamai block page")

            # Check page content for block message
            page_text = await page.text_content("body") or ""
            if "reference #" in page_text.lower() and "access denied" in page_text.lower():
                blocked = True
                block_reasons.append("Akamai block message in page content")

            # Check for product content
            try:
                await page.wait_for_selector('[data-testid="product-pod"], .product-card, .plp-pod', timeout=10000)
                products = await page.locator('[data-testid="product-pod"], .product-card, .plp-pod').count()
                print(f"Products found: {products}")
            except Exception:
                products = 0

            print("\n" + "=" * 60)
            if blocked:
                print("RESULT: BLOCKED BY AKAMAI")
                print(f"Reasons: {', '.join(block_reasons)}")
                print("\nPossible solutions:")
                print("1. Wait 24-48 hours for IP to cool down")
                print("2. Try a different network (mobile hotspot)")
                print("3. Check if Chrome is installed (not just Chromium)")
            elif products > 0:
                print("RESULT: SUCCESS! Page loaded with products.")
                print(f"Found {products} product cards on the page.")
                print("\nThe anti-fingerprinting is working!")
            else:
                print("RESULT: PARTIAL SUCCESS")
                print("Page loaded but no products found.")
                print("This might be a page layout issue, not a block.")
            print("=" * 60)

            # Keep browser open for manual inspection
            print("\nBrowser will stay open for 30 seconds for inspection...")
            print("Press Ctrl+C to close early.")
            try:
                await asyncio.sleep(30)
            except KeyboardInterrupt:
                pass

        except Exception as e:
            print(f"\nError during navigation: {e}")
            print("\nThis might indicate:")
            print("1. Network issues")
            print("2. Chrome not installed (install Google Chrome)")
            print("3. Akamai blocking at connection level")

        finally:
            await browser.close()


if __name__ == "__main__":
    print("\nStarting Akamai bypass test...")
    print("Make sure Google Chrome is installed on your system!")
    print("")

    asyncio.run(test_akamai_bypass())
