import asyncio
import random
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "apify_actor_seed" / "src"))
import main as actor_main

URL = "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"


async def run() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            timezone_id=random.choice(actor_main.TIMEZONES),
            locale=random.choice(actor_main.LOCALES),
            user_agent=random.choice(actor_main.USER_AGENTS),
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        await actor_main.apply_fingerprint_randomization(page)

        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        content = await page.content()
        Path("tmp_page_dump.html").write_text(content, encoding="utf-8")
        await page.screenshot(path="tmp_page_dump.png", full_page=True)

        await context.close()
        await browser.close()


asyncio.run(run())
