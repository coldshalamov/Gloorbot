"""
Given a list of Lowe's /c/ category hub URLs, find "Shop All" links on each page.

Behavior:
- Uses real Chrome (`channel="chrome"`), headed, persistent profile.
- For each /c/ URL:
  - Navigate (with warmup + human-ish delays).
  - If no "Shop All" links found, click "Show more" / "See more" if present, then re-scan.
  - Collect all /pl/ links that look like "Shop All".
  - Record which pages appear to have no Shop All (after show-more attempt).

Outputs:
- shop_all_audit_results.json
- SHOP_ALL_URLS.txt
- NO_SHOP_ALL_C_URLS.txt

Note:
This answers a narrow question: presence/absence of a "Shop All" link per /c/ hub.
It does not try to solve the full minimal-set problem.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE = "https://www.lowes.com"

IN_PATH = Path("c_links_input.txt")
OUT_JSON = Path("shop_all_audit_results.json")
OUT_SHOP_ALL = Path("SHOP_ALL_URLS.txt")
OUT_NO_SHOP_ALL = Path("NO_SHOP_ALL_C_URLS.txt")

PROFILE_DIR = Path(".playwright-profiles/url-audit")


def _abs(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return urljoin(BASE + "/", url)


def _norm(url: str) -> str:
    u = _abs(url)
    if not u:
        return ""
    parsed = urlparse(u)
    return f"{BASE}{parsed.path.rstrip('/')}"


def _is_pl(url: str) -> bool:
    try:
        return urlparse(url).path.startswith("/pl/")
    except Exception:
        return False


async def _human_pause(min_ms: int = 900, max_ms: int = 1700) -> None:
    await asyncio.sleep((min_ms + random.random() * (max_ms - min_ms)) / 1000)


async def _human_nudge(page: Any) -> None:
    try:
        await page.mouse.move(380 + random.random() * 700, 240 + random.random() * 420)
        await page.mouse.wheel(0, 140 + random.random() * 260)
    except Exception:
        pass


async def warmup(page: Any) -> None:
    await page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)
    await _human_nudge(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)


async def _extract_shop_all_pl(page: Any) -> list[str]:
    shop_all: list[str] = []
    # Scan anchor-like CTAs containing "Shop All"
    for sel in [
        "a:has-text('Shop All')",
        "a:has-text('Shop all')",
        "a[aria-label*='Shop All' i]",
        "a[data-testid*='shop-all' i]",
        "a[title*='Shop All' i]",
    ]:
        try:
            nodes = await page.locator(sel).all()
        except Exception:
            nodes = []
        for n in nodes[:30]:
            try:
                href = await n.get_attribute("href")
            except Exception:
                href = None
            if not href:
                continue
            u = _norm(href)
            if _is_pl(u) and u not in shop_all:
                shop_all.append(u)
    return shop_all


async def _click_show_more_if_present(page: Any) -> bool:
    # Try a few common "expand" controls.
    candidates = [
        "button:has-text('Show more')",
        "button:has-text('Show More')",
        "button:has-text('See more')",
        "button:has-text('See More')",
        "a:has-text('Show more')",
        "a:has-text('See more')",
        "[aria-label*='Show more' i]",
        "[aria-label*='See more' i]",
    ]
    for sel in candidates:
        loc = page.locator(sel).first
        try:
            if await loc.count() == 0:
                continue
        except Exception:
            continue
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        try:
            await _human_pause(400, 900)
            await loc.click(timeout=3000)
            await _human_pause(800, 1400)
            return True
        except Exception:
            continue
    return False


async def audit_one(page: Any, url: str) -> dict[str, Any]:
    out: dict[str, Any] = {"c_url": url, "blocked": False, "shop_all_pl": [], "show_more_clicked": False}

    for attempt in range(3):
        try:
            if attempt > 0:
                await warmup(page)
                await _human_pause(900, 1600)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await _human_pause(900, 1700)
            await _human_nudge(page)
            await _human_pause(700, 1300)
            break
        except Exception as e:
            out["error"] = str(e)
    else:
        return out

    # Block detection
    try:
        title = await page.title()
    except Exception:
        title = ""
    try:
        body_text = await page.locator("body").inner_text(timeout=3000)
    except Exception:
        body_text = ""
    if "Access Denied" in (title or "") or "Access Denied" in (body_text or "") or "Request blocked" in (title or ""):
        out["blocked"] = True
        out["title"] = title
        return out

    shop_all = await _extract_shop_all_pl(page)
    if not shop_all:
        clicked = await _click_show_more_if_present(page)
        out["show_more_clicked"] = clicked
        if clicked:
            shop_all = await _extract_shop_all_pl(page)

    out["shop_all_pl"] = shop_all
    out["title"] = title
    return out


def _load_urls() -> list[str]:
    if not IN_PATH.exists():
        raise FileNotFoundError(f"Missing {IN_PATH}")
    urls: list[str] = []
    for line in IN_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        u = _norm(line)
        if u and urlparse(u).path.startswith("/c/"):
            urls.append(u)
    # preserve order, dedupe
    seen = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def main() -> None:
    urls = _load_urls()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    all_shop_all: list[str] = []
    no_shop_all: list[str] = []

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

        await warmup(page)

        for idx, c_url in enumerate(urls, 1):
            # Periodic warmup (keeps session healthier)
            if idx % 15 == 0:
                await warmup(page)
            await _human_pause(900, 1700)
            print(f"[{idx}/{len(urls)}] {c_url}")
            rec = await audit_one(page, c_url)
            results.append(rec)

            pls = rec.get("shop_all_pl") or []
            if pls:
                for u in pls:
                    if u not in all_shop_all:
                        all_shop_all.append(u)
            else:
                no_shop_all.append(c_url)

        await context.close()

    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    OUT_SHOP_ALL.write_text("\n".join(all_shop_all) + ("\n" if all_shop_all else ""), encoding="utf-8")
    OUT_NO_SHOP_ALL.write_text("\n".join(no_shop_all) + ("\n" if no_shop_all else ""), encoding="utf-8")

    print("\nDONE")
    print(f"Total /c/ URLs: {len(urls)}")
    print(f"/c/ with >=1 Shop All /pl/: {len(urls) - len(no_shop_all)}")
    print(f"/c/ with NO Shop All /pl/: {len(no_shop_all)}")
    print(f"Unique Shop All /pl/ URLs found: {len(all_shop_all)}")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_SHOP_ALL}")
    print(f"Wrote {OUT_NO_SHOP_ALL}")


if __name__ == "__main__":
    asyncio.run(main())

