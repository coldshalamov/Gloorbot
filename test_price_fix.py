"""
Quick test script to verify the price extraction fix.
Tests the updated scraper against a known product page.
"""
import asyncio
import sys
from pathlib import Path

# Add PARALLEL to path so we can import the scraper
sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

from scraper import extract_prices_from_card
from playwright.async_api import async_playwright


async def test_price_extraction():
    """Test price extraction on a real Lowe's product page."""

    # The shower kit from your screenshot (SKU 1000212195)
    # This was showing incorrect 86% discount ($977.49 -> $131.00)
    test_url = "https://www.lowes.com/pd/DreamLine-French-Corner-2-Piece-36-in-W-x-36-in-L-x-75-in-H-Square-Corner-shower-kit-Corner-Drain-Base-and-Door-Black-Hardware-Included/1000212195"

    print("Testing price extraction fix...")
    print(f"URL: {test_url}\n")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        page = await browser.new_page()

        try:
            # Navigate to product page
            print("Loading product page...")
            await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Find the product card/container
            # On product detail pages, the price is usually in the main content area
            card = page.locator('main, [role="main"], .pdp-main-content, #pdp-main').first

            if await card.count() == 0:
                print("WARNING: Could not find main product container, using body")
                card = page.locator('body')

            print("Extracting prices...\n")

            # Enable price diagnostics for this test
            import os
            os.environ['GLOORBOT_PRICE_DIAGNOSTICS'] = '1'

            # Extract prices using the fixed function
            result = await extract_prices_from_card(card)

            print("=" * 60)
            print("RESULTS:")
            print("=" * 60)
            print(f"Current Price: {result['price']}")
            print(f"Was Price:     {result['was_price']}")
            print()

            # Calculate discount if we have both prices
            if result['price'] != 'N/A' and result['was_price']:
                try:
                    current = float(result['price'].replace('$', '').replace(',', ''))
                    was = float(result['was_price'].replace('$', '').replace(',', ''))
                    discount = ((was - current) / was) * 100
                    savings = was - current

                    print(f"Savings:       ${savings:,.2f}")
                    print(f"Discount:      {discount:.1f}%")
                    print()

                    # Validate the result
                    if discount > 90:
                        print("❌ FAIL: Discount > 90% - likely wrong!")
                        print("   This indicates the price extraction is still broken.")
                    elif discount < 0:
                        print("❌ FAIL: Negative discount - prices are backwards!")
                    elif discount >= 50 and discount <= 90:
                        print("✅ PASS: Discount in reasonable range (50-90%)")
                        print("   Price extraction appears to be working correctly.")
                    else:
                        print(f"⚠️  WARNING: Discount is {discount:.1f}%")
                        print("   This seems low for a clearance item, but may be correct.")

                except Exception as e:
                    print(f"Could not calculate discount: {e}")
            else:
                print("⚠️  No 'was price' found - item may not be on sale")

            print("=" * 60)

            # Show what extraction method was used
            print("\nTo see detailed extraction steps, check the price diagnostic logs")
            print("if GLOORBOT_PRICE_DIAGNOSTICS was enabled.\n")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_price_extraction())
