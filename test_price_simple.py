"""
Simple test to verify the price extraction fix works.
Tests against a live Lowe's page with known clearance items.
"""

import asyncio
import sys
import os
from pathlib import Path

# Enable price diagnostics
os.environ["GLOORBOT_PRICE_DIAGNOSTICS"] = "1"

# Add PARALLEL to path
sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

from playwright.async_api import async_playwright


async def test_shower_product():
    """Test the exact product from your screenshot."""

    # SKU 1000212195 - DreamLine shower (was showing 86% off incorrectly)
    test_url = "https://www.lowes.com/pl/Showers-Shower-stalls-enclosures-Showers-shower-doors-Bathroom/4294515648?inStock=1&storeNumber=1695"

    print("Testing price extraction on Lowe's clearance page...")
    print(f"URL: {test_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")

        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        try:
            print("Loading page...")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)  # Let page fully load

            print("Extracting prices using JavaScript (mimics the scraper)...\n")

            # Use the exact JavaScript extraction from the scraper
            result = await page.evaluate("""
                () => {
                    function normText(t) {
                        return (t || "").replace(/\\s+/g, " ").trim();
                    }

                    function normalizeMoney(m) {
                        if (!m) return null;
                        let s = String(m).replace(/\\s+/g, "");
                        if (!s.startsWith("$")) return null;
                        if (s.includes(".")) return s;
                        const raw = s.slice(1);
                        const digits = raw.replace(/,/g, "");
                        if (!/^\\d+$/.test(digits)) return s;

                        if (s.includes(",")) {
                            const lastGroup = s.split(",").pop() || "";
                            if (lastGroup.length > 3 && digits.length > 2) {
                                return "$" + digits.slice(0, -2) + "." + digits.slice(-2);
                            }
                            return "$" + digits + ".00";
                        }

                        if (digits.length >= 5) {
                            return "$" + digits.slice(0, -2) + "." + digits.slice(-2);
                        }
                        return "$" + digits + ".00";
                    }

                    function firstMoney(t) {
                        const s = String(t || "");
                        const re = /\\$\\s*\\d+(?:,\\d{3})*(?:\\.\\d{2}|\\d{2})?/g;
                        const matches = s.match(re) || [];
                        if (!matches.length) return null;

                        const candidates = [];
                        for (const raw of matches) {
                            const norm = normalizeMoney(raw);
                            if (norm) candidates.push({ raw, norm });
                        }
                        if (!candidates.length) return null;

                        function score(raw) {
                            const r = String(raw || "");
                            if (r.includes(".")) return 3;
                            if (r.includes(",")) {
                                const last = r.split(",").pop() || "";
                                if (last.length > 3) return 2;
                                return 1;
                            }
                            const digits = r.replace(/[^0-9]/g, "");
                            if (digits.length >= 4) return 2;
                            return 1;
                        }

                        function asNumber(norm) {
                            try {
                                return parseFloat(String(norm || "").replace(/[^0-9.]/g, "")) || 0;
                            } catch (e) {
                                return 0;
                            }
                        }

                        candidates.sort((a, b) => {
                            const sa = score(a.raw);
                            const sb = score(b.raw);
                            if (sb !== sa) return sb - sa;
                            return asNumber(b.norm) - asNumber(a.norm);
                        });
                        return candidates[0].norm;
                    }

                    function pickMoneyFromEl(el) {
                        if (!el) return null;
                        const ariaLabel = el.getAttribute("aria-label") || "";
                        const fromAria = firstMoney(ariaLabel);
                        if (fromAria) return fromAria;
                        const t = el.innerText || el.textContent || "";
                        return firstMoney(t);
                    }

                    // Find product cards
                    const cards = document.querySelectorAll('div.tile_group, [data-test="product-pod"]');
                    const results = [];

                    for (const card of Array.from(cards).slice(0, 5)) {
                        // Extract title
                        const titleEl = card.querySelector('[data-selector="splp-prd-ttl"]') ||
                                       card.querySelector('h3') ||
                                       card.querySelector('a[href*="/pd/"]');
                        const title = titleEl ? titleEl.textContent.trim() : '';

                        // Try data-testid selectors FIRST (the fix)
                        let currentPrice = null;
                        let wasPrice = null;
                        let method = 'none';

                        // NEW: data-testid strategy (from fix)
                        const testidCurrent = card.querySelector('[data-testid="current-price"], [data-testid="regular-price"]');
                        if (testidCurrent) {
                            currentPrice = pickMoneyFromEl(testidCurrent);
                            if (currentPrice) method = 'data-testid';
                        }

                        const testidWas = card.querySelector('[data-testid="was-price"]');
                        if (testidWas) {
                            wasPrice = pickMoneyFromEl(testidWas);
                        }

                        // FALLBACK: old data-selector strategy
                        if (!currentPrice) {
                            const selectorCurrent = card.querySelector('[data-selector="splp-prd-act-$"]');
                            if (selectorCurrent) {
                                currentPrice = pickMoneyFromEl(selectorCurrent);
                                if (currentPrice) method = 'data-selector';
                            }
                        }

                        if (!wasPrice) {
                            const selectorWas = card.querySelector('[data-selector="splp-prd-promo-was-$"]');
                            if (selectorWas) {
                                wasPrice = pickMoneyFromEl(selectorWas);
                            }
                        }

                        if (title && currentPrice) {
                            results.push({
                                title: title.substring(0, 60),
                                currentPrice,
                                wasPrice,
                                method
                            });
                        }
                    }

                    return results;
                }

            """)

            if not result:
                print("[FAIL] No products found on page!")
                return

            print("=" * 80)
            print(f"Found {len(result)} products with prices:\n")

            pass_count = 0
            fail_count = 0

            for i, product in enumerate(result, 1):
                title = product["title"]
                current = product["currentPrice"]
                was = product.get("wasPrice")
                method = product["method"]

                print(f"{i}. {title}")
                print(f"   Current: {current}")
                print(f"   Was:     {was or 'N/A'}")
                print(f"   Method:  {method}")

                if was and current:
                    try:
                        current_val = float(current.replace("$", "").replace(",", ""))
                        was_val = float(was.replace("$", "").replace(",", ""))
                        discount = ((was_val - current_val) / was_val) * 100
                        savings = was_val - current_val

                        print(f"   Savings: ${savings:,.2f} ({discount:.1f}% off)")

                        if discount > 90:
                            print(f"   [FAIL] Discount {discount:.1f}% is impossible!")
                            fail_count += 1
                        elif discount < 0:
                            print(f"   [FAIL] Negative discount!")
                            fail_count += 1
                        elif 50 <= discount <= 90:
                            print(f"   [PASS] Discount looks correct")
                            pass_count += 1
                        else:
                            print(f"   [WARN] Discount {discount:.1f}% seems unusual")
                    except Exception as e:
                        print(f"   [WARN] Could not calculate discount: {e}")

                print()

            print("=" * 80)
            print(f"Results: {pass_count} PASS, {fail_count} FAIL")

            if fail_count > 0:
                print("\n[FAIL] PRICE EXTRACTION STILL HAS ISSUES")
                print("The fix may not be working correctly.")
            elif pass_count > 0:
                print("\n[PASS] PRICE EXTRACTION APPEARS TO BE WORKING")
                print("The data-testid selectors are finding correct prices.")
            else:
                print("\n[WARN] Could not validate results (no discounted items found)")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_shower_product())
