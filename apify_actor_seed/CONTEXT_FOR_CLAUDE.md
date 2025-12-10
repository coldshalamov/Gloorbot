# Context for Claude (Python-only Apify Actor)

## Core goal
Build an Akamai-resistant Lowe's scraper as an Apify Actor in Python, using the provided Lowe's logic and anti-bot tactics. Run headful Playwright with stealth, residential proxies, pacing, and crash/block detection.

## Critical code to reuse (in this seed)
- `app/retailers/lowes.py`: store context, pagination, pickup filter on every page, block/crash detection, SKU parsing.
- `app/selectors.py`: selectors for product cards, pagination, store selection.
- `app/extractors/dom_utils.py`: human_wait, pagination helpers, price parsing.
- `app/playwright_env.py` + `app/anti_blocking.py`: launch args, headful default, stealth toggle, proxy/slowmo/wait tuning, mobile device pool, per-store profile cloning, nav semaphore.
- `app/multi_store.py`: URL blocklist/filtering, pacing/jitter, dedupe.
- Inputs: `LowesMap.txt`, `catalog/*.yml`, `app/config.yml`.
- Docs: `CRITICAL_FIXES_20251204.md`, `LOWES_URL_DISCOVERY_GUIDE.md`, `README.md`, `PROPOSED_SEED_PACKAGE.md`, `APIFY_ACTOR_CONTEXT.md`.

## Third-party references (Python-focused)
- `third_party/apify-sdk-python-README.md`: Actor lifecycle basics.
- `third_party/actor-whitepaper-README.md`: actor.json/Dockerfile/input schema philosophy.
- `third_party/fingerprint-suite-README.md`: fingerprinting concepts (for awareness; we use playwright-stealth here).
- `third_party/THIRD_PARTY_SNIPPETS.md`: Python snippets (Playwright+stealth, Actor lifecycle + proxy rotation, proxy rotation example, Playwright crawler example pointers).

## Minimal Dockerfile (headful-ready)
Use Apify’s Playwright image with Xvfb:
```
FROM apify/actor-python-playwright:3.12
COPY . ./
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "app.retailers.lowes"]  # replace with your Actor entrypoint
```

## Python Playwright + stealth snippet
```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False, args=[
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-infobars',
        '--lang=en-US',
        '--start-maximized',
        '--window-size=1440,960',
    ])
    context = await browser.new_context()
    page = await context.new_page()
    await stealth_async(page)
    await page.goto('https://example.com', wait_until='networkidle')
```

## Apify Actor lifecycle + proxy (Python)
```python
from apify import Actor
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        proxy_cfg = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'], country_code=inp.get('country_code') or 'US'
        )
        proxy_url = await proxy_cfg.new_url() if proxy_cfg else None
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                proxy={"server": proxy_url} if proxy_url else None,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-infobars',
                    '--lang=en-US',
                    '--start-maximized',
                    '--window-size=1440,960',
                ],
            )
            context = await browser.new_context()
            page = await context.new_page()
            await stealth_async(page)
            # TODO: call Lowe's scraping flow here
            await browser.close()
```

## Key behaviors to preserve from Lowe's code
- Headed Chromium; reuse/rotate profiles only if helpful; always allow stealth.
- Pickup filter clicked on every page; pagination via next/offset fallback to scroll.
- Block/crash detection after load; retry with backoff.
- Pacing/jitter: human_wait with multipliers; category/zip delay bounds; mouse jitter.
- URL filtering via `multi_store.py` blocklist; dedupe preserving order.

## Inputs/outputs
- Inputs: category URLs + store list (or use `LowesMap.txt` and `catalog/*.yml`), concurrency, proxy params, headless toggle, wait multipliers, slow-mo ms, device pool.
- Output: push to Apify Dataset: `{store_id, store_name, zip, sku, title, category, product_url, image_url, price, price_was, pct_off, availability, clearance, timestamp}`.

## Discovery note
Automated discovery is blocked; rely on provided category lists or manual inputs. Accept URLs via Actor input; skip discovery unless necessary.
