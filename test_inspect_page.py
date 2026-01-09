"""
Inspect what selectors are actually on the Lowe's page.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_page():
    test_url = "https://www.lowes.com/pl/Showers-Shower-stalls-enclosures-Showers-shower-doors-Bathroom/4294515648?inStock=1&storeNumber=1695"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        page = await browser.new_page()

        print(f"Loading: {test_url}\n")
        await page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(8)  # Wait for JavaScript rendering

        print("Checking what price selectors exist on the page...\n")

        result = await page.evaluate("""
            () => {
                const checks = {
                    'tile_group_count': document.querySelectorAll('div.tile_group').length,
                    'data_testid_current': document.querySelectorAll('[data-testid="current-price"]').length,
                    'data_testid_regular': document.querySelectorAll('[data-testid="regular-price"]').length,
                    'data_testid_was': document.querySelectorAll('[data-testid="was-price"]').length,
                    'data_selector_current': document.querySelectorAll('[data-selector="splp-prd-act-$"]').length,
                    'data_selector_was': document.querySelectorAll('[data-selector="splp-prd-promo-was-$"]').length,
                    'product_pods': document.querySelectorAll('[data-test="product-pod"]').length,
                    'pd_links': document.querySelectorAll('a[href*="/pd/"]').length,
                };

                // Get a sample product card HTML
                const firstCard = document.querySelector('div.tile_group') ||
                                 document.querySelector('[data-test="product-pod"]');

                checks.sample_html = firstCard ? firstCard.outerHTML.substring(0, 500) : 'No card found';

                return checks;
            }
        """)

        print("Selector counts:")
        for key, value in result.items():
            if key != 'sample_html':
                print(f"  {key}: {value}")

        print(f"\nSample HTML (first 500 chars):")
        print(result['sample_html'])

        print("\n\nPress Enter to close browser...")
        input()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_page())
