# Third-party snippets to harden the Lowe's Apify Actor

These are the out-of-the-box tools to harden the Actor in **Python** (Apify SDK + Playwright + stealth/proxy).

## 1) Playwright + stealth (Python)
Ensure `playwright-stealth` is installed.

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
- Run headful by default; apply stealth; reuse/rotate context as needed; pair with residential proxies.

## 2) Apify Actor lifecycle + proxy config (Python)
```python
from apify import Actor

async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        proxy = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code=inp.get('country_code') or 'US',
        )
        proxy_url = await proxy.new_url() if proxy else None
        # pass proxy_url to Playwright launch if needed
        dataset = await Actor.open_dataset()
        await dataset.push_data({'ok': True})
```
- Use `Actor.create_proxy_configuration()` for proxy rotation; push results to Dataset.

## 3) Proxy rotation example
Source: `docs/02_concepts/code/05_proxy_rotation.py`
```python
proxy_cfg = await Actor.create_proxy_configuration(proxy_urls=['http://proxy-1.com','http://proxy-2.com'])
url1 = await proxy_cfg.new_url()              # rotates
url2 = await proxy_cfg.new_url(session_id='a')# sticky per session_id
```

## 4) Playwright crawler example (Apify SDK)
Source: `docs/03_guides/code/03_playwright.py`
- Shows Actor lifecycle + request queue + Playwright launch (headless configurable) and dataset push.

## 5) Actor model reference
Source: `actor-whitepaper-README.md`
- Describes Actor inputs/outputs/storage; align `actor.json`, Dockerfile, input schema accordingly.

## Integration tips for the Lowe's Actor
- Stay Python-only; keep headful + stealth; rotate proxies; reuse/rotate profiles cautiously.
- Preserve human pacing from `app/playwright_env.py` and block/crash/pickup logic from `app/retailers/lowes.py`.
- Actor input: accept category URLs + store list (or use `LowesMap.txt`/catalog YAML); output to Dataset.\n
