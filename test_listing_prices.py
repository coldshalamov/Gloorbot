"""
Test price extraction on a product LISTING page (search results).
This is where the worker actually scrapes prices from.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

from scraper import extract_prices_from_card
from playwright.async_api import async_playwright


async def test_listing_prices():
    """Test price extraction from product listing/search results."""

    # Search for clearance/back aisle items at a specific store
    # This mimics what the worker does
    test_url = "https://www.lowes.com/pl/The-back-aisle/2021454685607?refinement=2&inStock=1&storeNumber=1089"

    print("Testing price extraction on product LISTING page...")
    print(f"URL: {test_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        page = await browser.new_page()

        try:
            print("Loading listing page...")
            await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(4)

            # Find product cards on the listing
            cards = await page.locator('div.tile_group, [data-test="product-pod"]').all()

            if not cards:
                print("No product cards found! Try a different URL or check selectors.")
                return

            print(f"Found {len(cards)} product cards\n")
            print("=" * 80)

            # Test first 5 cards
            for i, card in enumerate(cards[:5], 1):
                print(f"\nCard #{i}:")
                print("-" * 80)

                # Get title for context
                try:
                    title_el = card.locator('[data-selector="splp-prd-ttl"], h2, h3').first
                    if await title_el.count() > 0:
                        title = await title_el.inner_text()
                        print(f"Product: {title[:60]}...")
                except:
                    print("Product: (could not extract title)")

                # Extract prices
                result = await extract_prices_from_card(card)

                print(f"Current Price: {result['price']}")
                print(f"Was Price:     {result['was_price']}")

                # Calculate discount
                if result['price'] != 'N/A' and result['was_price']:
                    try:
                        current = float(result['price'].replace('$', '').replace(',', ''))
                        was = float(result['was_price'].replace('$', '').replace(',', ''))
                        discount = ((was - current) / was) * 100
                        savings = was - current

                        print(f"Savings:       ${savings:,.2f}")
                        print(f"Discount:      {discount:.1f}%")

                        # Flag suspicious discounts
                        if discount > 90:
                            print("  >>> WARNING: > 90% discount - SUSPICIOUS!")
                        elif discount < 0:
                            print("  >>> ERROR: Negative discount - PRICES BACKWARDS!")
                        elif discount >= 50:
                            print("  >>> OK: Good deal found")

                    except Exception as e:
                        print(f"  Error calculating: {e}")
                else:
                    print("  (No markdown/sale)")

            print("\n" + "=" * 80)
            print("\nTest complete. Check if any discounts > 90% (those are likely errors)")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_listing_prices())
