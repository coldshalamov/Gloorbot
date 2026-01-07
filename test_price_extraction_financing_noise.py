import asyncio

from playwright.async_api import async_playwright

import PARALLEL.scraper as scraper

from pathlib import Path
import json
import os


# Regression: Lowe's cards can include financing/monthly-payment snippets like "$125/mo"
# that must NOT be treated as the product's "now" price.
#
# Some cards also expose prices only via aria-label (not the splp-prd-* data-selectors),
# with the visible price split into multiple nodes ($ + 999 + .99). We must rely on
# aria-label "Actual Price" / "Was Price" to avoid concatenation mistakes.
HTML = """
<!doctype html>
<html>
  <body>
    <div class="tile_group" data-testid="product-card">
      <a href="/pd/Ashley-Heath-Products-2-500-Sq-Ft-Pedestal-Wood-Stove-2020-EPA-Certified/1003010946">
        <span data-selector="splp-prd-ttl">Ashley Hearth Products 2500-sq ft Wood Stove</span>
      </a>

      <!-- Real price, split across nodes; no data-selector on purpose -->
      <div id="50113084" aria-label="Actual Price $999.99">
        <span>$</span><span>999</span><span>.99</span>
      </div>

      <!-- Real was-price, aria-label only -->
      <div aria-label="Was Price $1,266.73">
        <span>$1,266.73</span>
      </div>

      <!-- Financing noise that previously could be misread as the product price -->
      <div data-testid="current-price">$125/mo Suggested payments with 8 month special financing.</div>
    </div>
  </body>
</html>
"""


async def test_price_extraction_financing_noise() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.set_content(HTML, wait_until="domcontentloaded")

        card = page.locator("div.tile_group").first
        assert await card.count() > 0, "expected at least one product card"

        diag_path = Path(__file__).with_suffix(".price_diag.jsonl")
        if diag_path.exists():
            diag_path.unlink()
        os.environ["GLOORBOT_PRICE_DIAGNOSTICS"] = "1"
        os.environ["GLOORBOT_PRICE_DIAG_PATH"] = str(diag_path)
        os.environ["GLOORBOT_PRICE_DIAG_MAXLEN"] = "500"

        prices = await scraper.extract_prices_from_card(card)
        assert prices["price"] == "$999.99", f"unexpected now price: {prices}"
        assert prices["was_price"] == "$1,266.73", f"unexpected was price: {prices}"

        assert diag_path.exists(), "expected price diagnostics jsonl to be written"
        lines = [ln.strip() for ln in diag_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 1, "expected at least one diagnostics event"
        evt = json.loads(lines[-1])
        assert evt.get("event") == "price_extract"
        assert evt.get("price") == "$999.99"
        assert evt.get("was_price") == "$1,266.73"
        assert isinstance(evt.get("steps"), list) and evt.get("steps"), "expected non-empty steps"

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_price_extraction_financing_noise())
