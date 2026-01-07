import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

import PARALLEL.scraper as scraper


FIXTURES_DIR = Path(__file__).parent / "tests" / "price_extraction" / "fixtures"


async def _extract_prices_from_fixture(filename: str) -> list[dict]:
    html = (FIXTURES_DIR / filename).read_text(encoding="utf-8")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.set_content(html, wait_until="domcontentloaded")

        tile_group = page.locator("div.tile_group").first
        assert await tile_group.count() > 0, "expected at least one tile_group"

        products = await scraper.extract_tile_group_products(tile_group)
        await browser.close()
        return products


async def test_fixture_mixed_tile_group() -> None:
    products = await _extract_prices_from_fixture("mixed_tile_group.html")
    assert len(products) == 2

    by_url = {p.get("url"): p for p in products}
    assert "https://www.lowes.com/pd/Product-A/111" in by_url
    assert "https://www.lowes.com/pd/Product-B/222" in by_url

    assert by_url["https://www.lowes.com/pd/Product-A/111"].get("price") == "$977.49"
    assert (
        by_url["https://www.lowes.com/pd/Product-A/111"].get("was_price") == "$1,149.99"
    )

    assert by_url["https://www.lowes.com/pd/Product-B/222"].get("price") == "$131.00"
    assert by_url["https://www.lowes.com/pd/Product-B/222"].get("was_price") == "$977.49"


async def test_fixture_financing_noise() -> None:
    products = await _extract_prices_from_fixture("financing_noise.html")
    assert len(products) == 1
    p = products[0]
    assert p.get("price") == "$999.99"
    assert p.get("was_price") == "$1,266.73"


async def test_fixture_savings_percentage_noise() -> None:
    products = await _extract_prices_from_fixture("savings_percentage.html")
    assert len(products) == 1
    p = products[0]
    assert p.get("price") == "$1,049.90"
    assert p.get("was_price") == "$1,399.99"


if __name__ == "__main__":
    asyncio.run(test_fixture_mixed_tile_group())
    asyncio.run(test_fixture_financing_noise())
    asyncio.run(test_fixture_savings_percentage_noise())

