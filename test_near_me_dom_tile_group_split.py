import asyncio
import urllib.parse

import pytest
from playwright.async_api import async_playwright

import PARALLEL.scraper as scraper


HTML = """
<!doctype html>
<html>
  <head><title>Test</title></head>
  <body>
    <div id="listItems" data-totaltile="2"></div>
    <div id="listingPagesSearchResults">
      <div class="tile_group">
        <!-- Tile 1: link comes first -->
        <div data-tile="1">
          <a href="/pd/Product-A/111">
            <span data-selector="splp-prd-ttl">Product A Shower Kit</span>
          </a>
        </div>

        <!-- Tile 2: price elements come before its link -->
        <div data-tile="2">
          <div data-selector="splp-prd-act-$" aria-label="Actual Price $131.00">$131.00</div>
          <span data-selector="splp-prd-promo-was-$" aria-label="Was Price $977.49">$977.49</span>
          <a href="/pd/Product-B/222">
            <span data-selector="splp-prd-ttl">Product B Faucet</span>
          </a>
        </div>

        <!-- Tile 1 prices later in DOM -->
        <div data-tile="1">
          <div data-selector="splp-prd-act-$" aria-label="Actual Price $977.49">$977.49</div>
          <span data-selector="splp-prd-promo-was-$" aria-label="Was Price $1,149.99">$1,149.99</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""


async def _no_sleep(*_args, **_kwargs):
    return None


async def _no_op(*_args, **_kwargs):
    return None


@pytest.mark.asyncio
async def test_near_me_dom_tile_group_split() -> None:
    # Speed up test by disabling scraper's intentional sleeps and human actions.
    scraper.asyncio.sleep = _no_sleep  # type: ignore[attr-defined]
    scraper.human_mouse_move = _no_op  # type: ignore[assignment]
    scraper.human_scroll = _no_op  # type: ignore[assignment]

    data_url = "data:text/html," + urllib.parse.quote(HTML)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        store_info = {
            "store_id": "1631",
            "name": "Bellingham, WA (#1631)",
            "city": "Bellingham",
            "state": "WA",
        }

        products = await scraper.scrape_category_page(page, data_url, store_info, page_num=1)

        # We should get BOTH products out of a tile_group, not a single mixed record.
        assert len(products) == 2, f"expected 2 products, got {len(products)}"

        by_url = {p.get("url"): p for p in products}
        assert "https://www.lowes.com/pd/Product-A/111" in by_url
        assert "https://www.lowes.com/pd/Product-B/222" in by_url

        # Critical: Product A must not inherit Product B's price.
        assert by_url["https://www.lowes.com/pd/Product-A/111"].get("price") == "$977.49"
        assert by_url["https://www.lowes.com/pd/Product-A/111"].get("was_price") == "$1,149.99"

        assert by_url["https://www.lowes.com/pd/Product-B/222"].get("price") == "$131.00"
        assert by_url["https://www.lowes.com/pd/Product-B/222"].get("was_price") == "$977.49"

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_near_me_dom_tile_group_split())
