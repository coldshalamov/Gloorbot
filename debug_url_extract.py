import asyncio
import random
from pathlib import Path

from playwright.async_api import async_playwright

from audit_all_urls import _extract_product_id_from_href, human_mouse_move, human_scroll, warmup_page


TEST_URLS = [
    "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984",
    "https://www.lowes.com/pl/AA-batteries-Batteries-Electrical/3574303452",
]

PROFILE_DIR = Path(".playwright-profiles/url-audit")


async def debug_url(page, url: str) -> None:
    print(f"\nTesting: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(1 + random.random())
    await human_mouse_move(page)
    await human_scroll(page)
    await asyncio.sleep(2 + random.random() * 2)

    title = await page.title()
    print(f"Title: {title}")

    for sel in [
        '[data-test="product-pod"]',
        'a[href*="/pd/"]',
        '[data-itemid]',
        "[data-sku]",
    ]:
        try:
            c = await page.locator(sel).count()
            if c:
                print(f"  {sel}: {c}")
        except Exception as e:
            print(f"  {sel}: error {e}")

    # Sample /pd/ hrefs
    try:
        pd_hrefs = await page.locator('a[href*="/pd/"]').evaluate_all(
            "els => els.slice(0, 10).map(a => a.getAttribute('href')).filter(Boolean)"
        )
        print("Sample /pd/ hrefs + parsed IDs:")
        for h in pd_hrefs[:10]:
            pid = _extract_product_id_from_href(h)
            print(f"  {h} -> {pid}")
    except Exception as e:
        print(f"/pd/ href extraction error: {e}")


async def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--lang=en-US",
            ],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("Warmup...")
        await warmup_page(page)

        for url in TEST_URLS:
            await debug_url(page, url)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())

