"""
Diagnostic Mode Scraper - Verify Everything Works Correctly

This scraper:
1. Takes screenshots at each step
2. Verifies "Pickup Today" filter is applied
3. Checks store context is set correctly
4. Validates products are local-only
5. Tests for blocking detection
6. Records detailed logs

Usage:
    python diagnostic_scraper.py --store-id 0061 --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Diagnostic output directory
DIAG_DIR = Path("diagnostic_output")
DIAG_DIR.mkdir(exist_ok=True)

class DiagnosticScraper:
    def __init__(self, store_id, store_url, category_url):
        self.store_id = store_id
        self.store_url = store_url
        self.category_url = category_url
        self.screenshots = []
        self.log_entries = []

    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        print(entry)
        self.log_entries.append(entry)

    async def screenshot(self, page, name):
        """Take screenshot for diagnostic"""
        path = DIAG_DIR / f"{len(self.screenshots):02d}_{name}.png"
        await page.screenshot(path=str(path))
        self.screenshots.append(str(path))
        self.log(f"Screenshot saved: {path}")

    async def check_blocking(self, page):
        """Check if we're blocked"""
        title = await page.title()
        content = await page.content()

        blocked = False
        reasons = []

        if "Access Denied" in title:
            blocked = True
            reasons.append("Title contains 'Access Denied'")

        if "blocked" in content.lower():
            blocked = True
            reasons.append("Content contains 'blocked'")

        if blocked:
            self.log(f"❌ BLOCKING DETECTED: {', '.join(reasons)}", "ERROR")
            await self.screenshot(page, "BLOCKED")
        else:
            self.log("✅ No blocking detected")

        return blocked

    async def verify_store_context(self, page):
        """Verify store is set correctly"""
        self.log("Verifying store context...")

        # Check for store indicator in page
        try:
            # Look for store name/ID in header
            store_element = page.locator(f"text=#{self.store_id}").first
            if await store_element.count() > 0:
                self.log(f"✅ Store #{self.store_id} detected in header")
                return True

            # Check cookies for store preference
            cookies = await page.context.cookies()
            store_cookie = next((c for c in cookies if 'store' in c['name'].lower()), None)
            if store_cookie:
                self.log(f"✅ Store cookie found: {store_cookie['name']} = {store_cookie['value']}")
                return True

            self.log("⚠️  Could not verify store context", "WARNING")
            return False

        except Exception as e:
            self.log(f"⚠️  Error verifying store: {e}", "WARNING")
            return False

    async def verify_pickup_filter(self, page):
        """Verify 'Pickup Today' filter is active"""
        self.log("Checking for 'Pickup Today' filter...")

        try:
            # Check URL for pickup filter parameter
            current_url = page.url
            if 'pickup' in current_url.lower() or 'fulfillment' in current_url.lower():
                self.log("✅ URL contains pickup/fulfillment parameter")
                return True

            # Check for filter UI element
            pickup_filter = page.locator("text=/Pickup Today|Get It Today|Available Today/i").first
            if await pickup_filter.count() > 0:
                is_selected = await pickup_filter.get_attribute("aria-selected") == "true"
                if is_selected:
                    self.log("✅ 'Pickup Today' filter is active")
                    return True
                else:
                    self.log("⚠️  'Pickup Today' filter exists but not selected", "WARNING")
                    return False

            self.log("❌ No 'Pickup Today' filter detected - products may not be local!", "ERROR")
            return False

        except Exception as e:
            self.log(f"⚠️  Error checking pickup filter: {e}", "WARNING")
            return False

    async def analyze_products(self, page):
        """Count and analyze products on page"""
        self.log("Analyzing products on page...")

        # Try multiple selectors
        selectors = [
            '[class*="ProductCard"]',
            '[class*="product-card"]',
            'article',
            '[data-test="product-pod"]'
        ]

        best_count = 0
        best_selector = None

        for selector in selectors:
            cards = await page.locator(selector).count()
            self.log(f"  Selector '{selector}': {cards} elements")
            if cards > best_count:
                best_count = cards
                best_selector = selector

        self.log(f"✅ Best selector: '{best_selector}' ({best_count} products)")

        # Check first product for availability
        if best_count > 0:
            first_card = page.locator(best_selector).first

            # Look for availability indicators
            availability_text = await first_card.inner_text()
            if "pickup" in availability_text.lower() or "available" in availability_text.lower():
                self.log("✅ First product shows pickup/availability info")
            else:
                self.log("⚠️  First product might not show local availability", "WARNING")

        return best_count

    async def run_diagnostic(self):
        """Run full diagnostic test"""
        self.log("="*70)
        self.log("DIAGNOSTIC MODE - Scraper Validation")
        self.log("="*70)
        self.log(f"Store ID: {self.store_id}")
        self.log(f"Store URL: {self.store_url}")
        self.log(f"Category URL: {self.category_url}")
        self.log("="*70)

        async with async_playwright() as p:
            self.log("Launching Chrome browser (headed mode)...")

            # Create profile directory
            profile_dir = Path(f".playwright-profiles/diagnostic_{self.store_id}")
            profile_dir.mkdir(parents=True, exist_ok=True)

            context = await p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,  # CRITICAL
                channel='chrome',
                viewport={'width': 1440, 'height': 900},
                args=[
                    '--disable-blink-features=AutomationControlled',
                ]
            )

            page = context.pages[0] if context.pages else await context.new_page()

            try:
                # Step 1: Visit homepage for warmup
                self.log("\n--- STEP 1: Homepage Warmup ---")
                await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(3)
                await self.screenshot(page, "01_homepage")

                blocked = await self.check_blocking(page)
                if blocked:
                    self.log("❌ Blocked on homepage! Cannot continue.", "ERROR")
                    return

                # Step 2: Set store context
                self.log("\n--- STEP 2: Set Store Context ---")
                await page.goto(self.store_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)
                await self.screenshot(page, "02_store_page")

                # Try to click "Set Store" button
                set_store_clicked = False
                for selector in ["button:has-text('Set Store')", "button:has-text('Set as My Store')"]:
                    try:
                        btn = page.locator(selector).first
                        if await btn.is_visible(timeout=3000):
                            self.log(f"Found button: {selector}")
                            await btn.click(timeout=5000)
                            await asyncio.sleep(2)
                            await self.screenshot(page, "03_store_set")
                            set_store_clicked = True
                            self.log("✅ Store set button clicked")
                            break
                    except:
                        continue

                if not set_store_clicked:
                    self.log("⚠️  Could not click 'Set Store' button", "WARNING")

                # Verify store context
                await self.verify_store_context(page)

                # Step 3: Navigate to category
                self.log("\n--- STEP 3: Navigate to Category ---")
                await page.goto(self.category_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(2)
                await self.screenshot(page, "04_category_initial")

                blocked = await self.check_blocking(page)
                if blocked:
                    self.log("❌ Blocked on category page!", "ERROR")
                    return

                # Step 4: Check for and apply "Pickup Today" filter
                self.log("\n--- STEP 4: Apply Pickup Today Filter ---")

                # Look for filter button/link
                pickup_selectors = [
                    "button:has-text('Pickup')",
                    "a:has-text('Pickup')",
                    "button:has-text('Get It Today')",
                    "[data-test*='pickup']",
                    "text=/Pickup Today|Available Today/i"
                ]

                filter_applied = False
                for selector in pickup_selectors:
                    try:
                        filter_elem = page.locator(selector).first
                        if await filter_elem.count() > 0:
                            self.log(f"Found pickup filter: {selector}")
                            await filter_elem.click(timeout=5000)
                            await asyncio.sleep(3)  # Wait for filter to apply
                            await self.screenshot(page, "05_filter_applied")
                            filter_applied = True
                            self.log("✅ Pickup filter clicked")
                            break
                    except Exception as e:
                        continue

                if not filter_applied:
                    self.log("⚠️  Could not find/click pickup filter - products may not be local!", "WARNING")

                # Verify filter is active
                await self.verify_pickup_filter(page)

                # Step 5: Analyze products
                self.log("\n--- STEP 5: Product Analysis ---")
                product_count = await self.analyze_products(page)

                await self.screenshot(page, "06_final_state")

                # Step 6: Extract sample product
                if product_count > 0:
                    self.log("\n--- STEP 6: Extract Sample Product ---")

                    card = page.locator('[class*="ProductCard"]').first
                    try:
                        # Title
                        title_elem = card.locator("a[href*='/pd/']").first
                        title = await title_elem.inner_text()
                        href = await title_elem.get_attribute("href")

                        # Price
                        price_elem = card.locator("[data-testid='current-price']").first
                        price = await price_elem.inner_text() if await price_elem.count() > 0 else "N/A"

                        self.log(f"Sample product:")
                        self.log(f"  Title: {title[:60]}...")
                        self.log(f"  URL: {href}")
                        self.log(f"  Price: {price}")

                    except Exception as e:
                        self.log(f"⚠️  Could not extract sample product: {e}", "WARNING")

            finally:
                await context.close()

        # Save diagnostic report
        self.save_report()

    def save_report(self):
        """Save diagnostic report"""
        report_path = DIAG_DIR / f"diagnostic_report_{self.store_id}.txt"

        with open(report_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("DIAGNOSTIC SCRAPER REPORT\n")
            f.write("="*70 + "\n\n")

            f.write("Store ID: " + self.store_id + "\n")
            f.write("Store URL: " + self.store_url + "\n")
            f.write("Category URL: " + self.category_url + "\n")
            f.write("Timestamp: " + datetime.now().isoformat() + "\n\n")

            f.write("="*70 + "\n")
            f.write("LOG ENTRIES\n")
            f.write("="*70 + "\n\n")

            for entry in self.log_entries:
                f.write(entry + "\n")

            f.write("\n" + "="*70 + "\n")
            f.write("SCREENSHOTS\n")
            f.write("="*70 + "\n\n")

            for screenshot in self.screenshots:
                f.write(f"- {screenshot}\n")

        self.log(f"\n✅ Diagnostic report saved to: {report_path}")


async def main():
    parser = argparse.ArgumentParser(description='Diagnostic Scraper')
    parser.add_argument('--store-id', required=True, help='Store ID (e.g., 0061)')
    parser.add_argument('--category-url', required=True, help='Category URL to test')
    args = parser.parse_args()

    # Load store URL from LowesMap.txt
    store_url = None
    with open('LowesMap.txt') as f:
        for line in f:
            if f'/{args.store_id}' in line and '/store/' in line:
                store_url = line.strip()
                break

    if not store_url:
        print(f"❌ Store {args.store_id} not found in LowesMap.txt")
        sys.exit(1)

    scraper = DiagnosticScraper(args.store_id, store_url, args.category_url)
    await scraper.run_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())
