import asyncio

import pytest
from playwright.async_api import async_playwright

import PARALLEL.scraper as scraper


HTML = """
<!doctype html>
<html>
  <body>
    <div class="tile_group">
      <div data-tile="1">
        <a href="/pd/Product-A/111">
          <span data-selector="splp-prd-ttl">BrandA 24-in Dishwasher</span>
        </a>
        <div data-selector="splp-prd-act-$" aria-label="Actual Price $399.00">$399.00</div>
        <span data-selector="splp-prd-promo-was-$" aria-label="Was Price $499.00">$499.00</span>
      </div>
      <div data-tile="2">
        <a href="/pd/Product-B/222">
          <span data-selector="splp-prd-ttl">BrandB 24-in Dishwasher</span>
        </a>
        <div data-selector="splp-prd-act-$" aria-label="Actual Price $599.00">$599.00</div>
        <span data-selector="splp-prd-promo-was-$" aria-label="Was Price $699.00">$699.00</span>
      </div>
    </div>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_tile_group_extraction() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.set_content(HTML, wait_until="domcontentloaded")

        tile = page.locator("div.tile_group").first
        assert await tile.count() > 0, "expected at least one tile_group"

        # New helper should split a tile_group into per-product records
        products = await scraper.extract_tile_group_products(tile)
        assert len(products) == 2, "expected two products from tile_group"

        urls = sorted([p.get("url") for p in products])
        assert urls == [
            "https://www.lowes.com/pd/Product-A/111",
            "https://www.lowes.com/pd/Product-B/222",
        ], "unexpected product urls"

        prices = sorted([p.get("price") for p in products])
        assert prices == ["$399.00", "$599.00"], "unexpected prices"

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_tile_group_extraction())
