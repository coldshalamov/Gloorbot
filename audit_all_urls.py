"""
Audit ALL 515 URLs from LowesMap.txt
Extracts product count and sample product IDs for duplicate detection

Run this overnight - takes several hours
"""

import asyncio
import json
import random
import re
from pathlib import Path
from playwright.async_api import async_playwright

# Config
LOWES_MAP_CANDIDATES = [
    Path("LowesMap.txt"),
    Path("lowes-apify-actor/LowesMap.txt"),
]
OUTPUT_FILE = Path("url_audit_results.json")
OUTPUT_JSONL = Path("url_audit_results.jsonl")
PROFILE_DIR = Path(".playwright-profiles/url-audit")


async def human_mouse_move(page) -> None:
    viewport = page.viewport_size
    width = viewport.get("width", 1440) if viewport else 1440
    height = viewport.get("height", 900) if viewport else 900

    start_x = random.random() * width * 0.3
    start_y = random.random() * height * 0.3
    end_x = width * 0.4 + random.random() * width * 0.4
    end_y = height * 0.4 + random.random() * height * 0.4

    steps = 10 + int(random.random() * 10)
    for i in range(steps + 1):
        progress = i / steps
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep((15 + random.random() * 25) / 1000)


async def human_scroll(page) -> None:
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((40 + random.random() * 80) / 1000)

async def warmup_page(page):
    """Required Akamai bypass warmup"""
    await page.goto('https://www.lowes.com/', wait_until='domcontentloaded', timeout=60000)
    # Give Akamai time to finish any challenge.
    await asyncio.sleep(3 + random.random() * 2)

    # Simulate human: light mouse + scroll, then wait ~2s
    try:
        await human_mouse_move(page)
        await asyncio.sleep(0.8 + random.random() * 0.8)
        await human_scroll(page)
        await asyncio.sleep(1.2 + random.random() * 1.2)
        await human_mouse_move(page)
    except Exception:
        pass

    await asyncio.sleep(1.5 + random.random() * 1.5)

    # Wait for common Akamai / bot-manager cookies to appear.
    # If these never appear, category pages tend to immediately return "Access Denied".
    for _ in range(30):  # up to ~30s
        try:
            cookies = await page.context.cookies("https://www.lowes.com/")
            abck = next((c for c in cookies if isinstance(c, dict) and c.get("name") == "_abck"), None)
            if abck and isinstance(abck.get("value"), str) and "~0~" in abck["value"]:
                return
        except Exception:
            pass
        await asyncio.sleep(1)

def _extract_product_id_from_href(href: str | None) -> str | None:
    if not href:
        return None
    # Common formats:
    # - /pd/<name>/<digits>
    # - https://www.lowes.com/pd/<name>/<digits>
    # - .../<digits>?...
    m = re.search(r"/(\d+)(?:\?|$)", href)
    return m.group(1) if m else None

async def test_url(page, url, index, total):
    """Test one URL and return stats"""
    print(f"\n[{index}/{total}] Testing: {url}")

    try:
        # Navigate
        await asyncio.sleep(1 + random.random())  # 1-2s between navigations
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        # Human-like behavior after navigation (critical for Akamai).
        await asyncio.sleep(1 + random.random())
        try:
            await human_mouse_move(page)
            await asyncio.sleep(0.4 + random.random() * 0.6)
            await human_scroll(page)
        except Exception:
            pass
        await asyncio.sleep(1 + random.random())  # user requested 1-2s

        # Check blocking
        title = None
        for _ in range(3):
            try:
                title = await page.title()
                break
            except Exception:
                # Some Lowe's pages trigger a follow-up navigation after DOMContentLoaded.
                await asyncio.sleep(0.75)
        title = title or ""
        if "Access Denied" in title or "Request blocked" in title:
            print("  BLOCKED")
            return {"url": url, "blocked": True, "count": 0, "product_ids": [], "title": title}

        # Count products
        selectors = [
            '[data-test="product-pod"]',
            '[class*="ProductCard"]',
            '[class*="product-card"]',
            'article',
        ]
        max_count = 0
        for sel in selectors:
            count = await page.locator(sel).count()
            if count > max_count:
                max_count = count

        # Get sample product IDs
        product_ids: list[str] = []
        # 1) Try /pd/ links (best signal)
        try:
            await page.locator('a[href*="/pd/"], a[href*="://www.lowes.com/pd/"]').first.wait_for(timeout=8000)
        except Exception:
            pass
        product_links = await page.locator('a[href*="/pd/"], a[href*="://www.lowes.com/pd/"]').all()
        for link in product_links[:80]:
            href = await link.get_attribute("href")
            pid = _extract_product_id_from_href(href)
            if pid and pid not in product_ids:
                product_ids.append(pid)

        # 2) Fall back to common product ID attributes if links aren't available yet
        if len(product_ids) < 10:
            try:
                raw_vals = await page.locator(
                    "[data-itemid], [data-item-id], [data-sku], [data-productid], [data-product-id]"
                ).evaluate_all(
                    """els => els.slice(0, 500).map(e =>
                      e.getAttribute('data-itemid') ||
                      e.getAttribute('data-item-id') ||
                      e.getAttribute('data-sku') ||
                      e.getAttribute('data-productid') ||
                      e.getAttribute('data-product-id')
                    )"""
                )
                for v in raw_vals:
                    if not v:
                        continue
                    m = re.search(r"(\d{6,})", str(v))
                    if m:
                        pid = m.group(1)
                        if pid not in product_ids:
                            product_ids.append(pid)
            except Exception:
                pass

        # 3) Debug/last-resort: capture a few hrefs inside product pods and try to parse IDs from them.
        sample_hrefs: list[str] | None = None
        if not product_ids and max_count > 0:
            try:
                sample_hrefs = await page.locator('[data-test="product-pod"] a').evaluate_all(
                    "els => els.slice(0, 40).map(a => a.getAttribute('href')).filter(Boolean)"
                )
                if sample_hrefs:
                    for href in sample_hrefs[:40]:
                        pid = _extract_product_id_from_href(href)
                        if pid and pid not in product_ids:
                            product_ids.append(pid)
            except Exception:
                sample_hrefs = None

        # Breadcrumb (best-effort)
        breadcrumb = None
        try:
            crumb = await page.locator('nav[aria-label="Breadcrumb"]').first.inner_text(timeout=2000)
            breadcrumb = " > ".join([c.strip() for c in crumb.splitlines() if c.strip()])
        except Exception:
            breadcrumb = None

        print(f"  OK: {max_count} products, {len(product_ids)} IDs extracted")

        return {
            "url": url,
            "blocked": False,
            "count": max_count,
            "product_ids": product_ids[:10],  # Keep first 10
            "title": title,
            "breadcrumb": breadcrumb,
            "sample_hrefs": sample_hrefs[:10] if sample_hrefs else None,
        }

    except Exception as e:
        # Avoid unicode in console output on Windows cp1252 terminals.
        print(f"  Error: {e}")
        return {"url": url, "error": str(e), "blocked": False, "count": 0, "product_ids": []}

def _resolve_lowes_map_path() -> Path:
    for candidate in LOWES_MAP_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find LowesMap.txt in {', '.join(str(p) for p in LOWES_MAP_CANDIDATES)}")

def _load_existing_results() -> dict[str, dict]:
    if not OUTPUT_FILE.exists():
        return {}
    try:
        data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {item.get("url"): item for item in data if isinstance(item, dict) and item.get("url")}
    except Exception:
        pass
    return {}

def _append_jsonl(record: dict) -> None:
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

async def main():
    # Load URLs
    lowes_map = _resolve_lowes_map_path()
    urls = []
    with open(lowes_map, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith('https://www.lowes.com/pl/'):
                urls.append(line)

    print(f"Loaded {len(urls)} category URLs from LowesMap.txt")
    print(f"Output will be saved to: {OUTPUT_FILE}")
    print(f"\nStarting audit... this will take several hours")
    print("=" * 70)

    # Setup browser
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_results()
    if existing:
        print(f"Resuming: found {len(existing)} existing results in {OUTPUT_FILE}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            channel='chrome',
            viewport={'width': 1440, 'height': 900},
            locale='en-US',
            timezone_id='America/Los_Angeles',
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--lang=en-US",
            ],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Initial warmup (required for Akamai)
        print("Initial warmup...")
        await warmup_page(page)

        # Test all URLs
        results: list[dict] = list(existing.values()) if existing else []
        done_ok = {r.get("url") for r in results if r.get("url") and not r.get("blocked") and "error" not in r}

        for i, url in enumerate(urls, 1):
            if url in done_ok:
                print(f"\n[{i}/{len(urls)}] Skipping already-successful: {url}")
                continue

            # Try the URL; if blocked, re-warm and retry a couple times.
            result = await test_url(page, url, i, len(urls))
            if result.get("blocked") or result.get("error"):
                for attempt in range(2):
                    print(f"  Retry after warmup ({attempt+1}/2)")
                    try:
                        await warmup_page(page)
                    except Exception:
                        pass
                    result = await test_url(page, url, i, len(urls))
                    if not result.get("blocked") and not result.get("error"):
                        break

            # Replace existing record for same URL if present
            if result.get("url") in existing:
                results = [r for r in results if r.get("url") != result.get("url")]
            results.append(result)
            existing[result.get("url")] = result
            _append_jsonl(result)

            # Save progress every 25 URLs
            if i % 25 == 0:
                with open(OUTPUT_FILE, 'w', encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"\nSAVED progress ({i}/{len(urls)})")

        # Final save
        with open(OUTPUT_FILE, 'w', encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        await context.close()

    # Summary
    print("\n" + "=" * 70)
    print("AUDIT COMPLETE!")
    print("=" * 70)
    blocked = sum(1 for r in results if r.get("blocked"))
    errors = sum(1 for r in results if "error" in r)
    empty = sum(1 for r in results if r.get("count", 0) == 0 and not r.get("blocked"))

    print(f"Total URLs tested: {len(results)}")
    print(f"Blocked: {blocked}")
    print(f"Errors: {errors}")
    print(f"Empty (0 products): {empty}")
    print(f"Success: {len(results) - blocked - errors}")
    print(f"\nResults saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
