"""
Test script to debug the pickup filter behavior on Lowe's
"""
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright


async def human_mouse_move(page):
    """Human-like mouse movement"""
    viewport = page.viewport_size
    width = viewport.get('width', 1440) if viewport else 1440
    height = viewport.get('height', 900) if viewport else 900

    start_x = random.random() * width * 0.3
    start_y = random.random() * height * 0.3
    end_x = width * 0.4 + random.random() * width * 0.4
    end_y = height * 0.4 + random.random() * height * 0.4

    steps = 10 + int(random.random() * 10)
    for i in range(steps + 1):
        progress = i / steps
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep((18 + random.random() * 30) / 1000)


async def human_scroll(page):
    """Human-like scrolling"""
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((45 + random.random() * 90) / 1000)


async def main():
    profile_dir = Path(".playwright-profiles/test-pickup")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Try Chrome first, fall back to Chromium
        launch_kwargs = {
            "headless": False,
            "viewport": {"width": 1440, "height": 900},
            "locale": "en-US",
            "timezone_id": "America/Los_Angeles",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-gpu",
                "--no-sandbox",
            ],
        }

        try:
            context = await p.chromium.launch_persistent_context(str(profile_dir), channel="chrome", **launch_kwargs)
            print("[INFO] Using Chrome")
        except Exception as e:
            print(f"[INFO] Chrome not available ({e}), using Chromium")
            context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)

        page = context.pages[0] if context.pages else await context.new_page()

        # Step 1: Warmup on homepage
        print("\n[STEP 1] Warming up on homepage...")
        await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3.5 + random.random() * 2)
        await human_mouse_move(page)
        await asyncio.sleep(1 + random.random())
        await human_scroll(page)
        await asyncio.sleep(1.5 + random.random() * 1.5)

        title = await page.title()
        print(f"[INFO] Homepage title: {title}")

        # Check for blocking
        if "Access Denied" in title or "Robot" in title:
            print("[ERROR] BLOCKED on homepage!")
            await context.close()
            return

        # Step 2: Set store
        print("\n[STEP 2] Setting store...")
        store_url = "https://www.lowes.com/store/WA-Seattle/0004"
        await page.goto(store_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(2)

        for selector in ["button:has-text('Set Store')", "button:has-text('Set as My Store')"]:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click(timeout=8000)
                    print(f"[INFO] Clicked: {selector}")
                    await asyncio.sleep(1.5)
                    break
            except Exception as e:
                continue

        # Step 3: Go to a category page
        print("\n[STEP 3] Navigating to category page...")
        category_url = "https://www.lowes.com/pl/Power-tools-Tools/4294607842"
        await page.goto(category_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)

        await human_mouse_move(page)
        await asyncio.sleep(0.5)

        title = await page.title()
        print(f"[INFO] Category page title: {title}")

        # Check for blocking
        if "Access Denied" in title or "Robot" in title:
            print("[ERROR] BLOCKED on category page!")
            await context.close()
            return

        # Step 4: Analyze the filter panel
        print("\n[STEP 4] Analyzing filter panel...")

        # Scroll to top to see filters
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

        # Look for "Pickup & Delivery" section
        pickup_delivery_section = page.locator('text="Pickup & Delivery"').first
        if await pickup_delivery_section.count() > 0:
            print("[INFO] Found 'Pickup & Delivery' section")

            # Check if it's a button/toggle that needs expanding
            parent = pickup_delivery_section.locator("xpath=ancestor::button | ancestor::summary").first
            if await parent.count() > 0:
                expanded = await parent.get_attribute("aria-expanded")
                print(f"[INFO] Section expanded state: {expanded}")
                if expanded == "false":
                    print("[INFO] Clicking to expand section...")
                    await parent.click()
                    await asyncio.sleep(0.5)
        else:
            print("[WARN] Could not find 'Pickup & Delivery' section")

        # Look for "Pickup Today at" checkbox
        print("\n[STEP 5] Looking for 'Pickup Today' checkbox...")

        # Method 1: Find all checkboxes and check their context
        checkboxes = await page.locator('input[type="checkbox"]').all()
        print(f"[INFO] Found {len(checkboxes)} checkboxes on page")

        for i, cb in enumerate(checkboxes[:10]):  # Check first 10
            try:
                # Get parent container text
                parent = cb.locator("xpath=ancestor::div[1] | ancestor::label[1] | ancestor::li[1]").first
                if await parent.count() > 0:
                    text = await parent.inner_text()
                    text_preview = text[:100].replace('\n', ' ')
                    checked = await cb.is_checked()
                    print(f"  Checkbox {i}: checked={checked}, text='{text_preview}...'")

                    if "Pickup Today" in text:
                        print(f"  >>> FOUND 'Pickup Today' checkbox at index {i}!")
            except Exception as e:
                pass

        # Method 2: Use JavaScript to find the pickup checkbox
        print("\n[STEP 6] Using JavaScript to find pickup checkbox...")

        result = await page.evaluate("""
            () => {
                const info = {
                    checkboxes: [],
                    pickupFound: false,
                    pickupElement: null
                };

                // Find all checkboxes
                const checkboxes = document.querySelectorAll('input[type="checkbox"]');

                for (const cb of checkboxes) {
                    const parent = cb.closest('div, label, li');
                    if (parent) {
                        const text = parent.textContent || '';
                        if (text.includes('Pickup Today')) {
                            info.pickupFound = true;
                            info.pickupElement = {
                                id: cb.id,
                                name: cb.name,
                                checked: cb.checked,
                                parentText: text.slice(0, 200)
                            };
                        }
                    }
                }

                // Also look for any element with "Pickup Today at"
                const xpath = document.evaluate(
                    "//*[contains(text(), 'Pickup Today at')]",
                    document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                );
                if (xpath.singleNodeValue) {
                    info.pickupTodayAtElement = {
                        tagName: xpath.singleNodeValue.tagName,
                        text: xpath.singleNodeValue.textContent.slice(0, 200)
                    };
                }

                return info;
            }
        """)

        print(f"[INFO] JavaScript result: {result}")

        # Step 7: Try clicking the pickup checkbox
        if result.get('pickupFound'):
            print("\n[STEP 7] Attempting to click pickup checkbox via JavaScript...")

            click_result = await page.evaluate("""
                () => {
                    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                    for (const cb of checkboxes) {
                        const parent = cb.closest('div, label, li');
                        if (parent && parent.textContent.includes('Pickup Today')) {
                            const wasChecked = cb.checked;
                            if (!wasChecked) {
                                cb.click();
                                return {clicked: true, wasChecked: false, nowChecked: cb.checked};
                            }
                            return {clicked: false, wasChecked: true, nowChecked: cb.checked};
                        }
                    }
                    return {error: 'Checkbox not found'};
                }
            """)

            print(f"[INFO] Click result: {click_result}")

            if click_result.get('clicked'):
                print("[INFO] Waiting for page to update...")
                await asyncio.sleep(2)

                # Check if URL changed
                new_url = page.url
                print(f"[INFO] Current URL: {new_url[:100]}...")

                # Wait for network
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
        else:
            print("\n[WARN] Pickup checkbox not found, skipping click test")

        # Step 8: Look for product cards
        print("\n[STEP 8] Looking for product cards...")

        selectors = [
            "[data-test='product-pod']",
            "[data-test='productPod']",
            "div[data-itemid]",
            "li[data-itemid]",
            "[data-itemid]",
            "li:has(a[href*='/pd/'])",
            "article:has(a[href*='/pd/'])",
            '[class*="ProductCard"]',
            '[class*="product-card"]',
        ]

        for sel in selectors:
            cards = await page.locator(sel).all()
            if cards:
                print(f"[INFO] Selector '{sel}': {len(cards)} cards")

        # Final summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)

        # Get product count from page
        product_count_el = page.locator('text=/\\d+ Results?|\\d+ products?/i').first
        if await product_count_el.count() > 0:
            count_text = await product_count_el.inner_text()
            print(f"[INFO] Product count from page: {count_text}")

        # Keep browser open for manual inspection
        print("\n[INFO] Browser will stay open for 30 seconds for manual inspection...")
        await asyncio.sleep(30)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
