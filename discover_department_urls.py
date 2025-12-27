"""
Discover Lowe's department listing URLs starting from /c/Departments.

Goal:
- Build a high-confidence "candidate universe" of listing endpoints:
  - Direct /pl/ links from the Departments page
  - "Shop All" /pl/ links inside /c/ category pages
  - For /c/ pages without "Shop All", capture the *first* "Shop By ..." module's /pl/ links
    (and record other modules for later analysis, but don't automatically include them).

Outputs:
- discovered/departments_raw.json     (full provenance + modules)
- discovered/pl_candidates.txt        (all /pl/ candidate URLs in discovery order)
- discovered/c_visited.txt            (visited /c/ pages)
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


BASE = "https://www.lowes.com"
START = "https://www.lowes.com/c/Departments"

OUT_DIR = Path("discovered")
OUT_RAW = OUT_DIR / "departments_raw.json"
OUT_PL = OUT_DIR / "pl_candidates.txt"
OUT_C = OUT_DIR / "c_visited.txt"

_AUDIT_PROFILE = Path(".playwright-profiles/url-audit")
PROFILE_PARENT = Path(".playwright-profiles/department-discovery")
PROFILE_DIR = _AUDIT_PROFILE if _AUDIT_PROFILE.exists() else (PROFILE_PARENT / f"run_{int(time.time())}")


def _abs(url: str) -> str:
    if url.startswith("http"):
        return url
    return urljoin(BASE + "/", url)


def _norm(url: str) -> str:
    u = _abs(url)
    parsed = urlparse(u)
    return f"{BASE}{parsed.path.rstrip('/')}"


def _is_pl(url: str) -> bool:
    try:
        return urlparse(url).path.startswith("/pl/")
    except Exception:
        return False


def _is_c(url: str) -> bool:
    try:
        return urlparse(url).path.startswith("/c/")
    except Exception:
        return False


async def _human_pause(min_ms: int = 900, max_ms: int = 1700) -> None:
    await asyncio.sleep((min_ms + random.random() * (max_ms - min_ms)) / 1000)


async def _warmup(page: Any) -> None:
    await page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3 + random.random() * 2)
    try:
        await page.mouse.move(400 + random.random() * 600, 250 + random.random() * 350)
        await page.mouse.wheel(0, 140 + random.random() * 220)
    except Exception:
        pass
    await asyncio.sleep(1.5 + random.random() * 1.5)


async def _get_all_hrefs(page: Any) -> list[str]:
    # Best-effort: get all anchors hrefs visible in the DOM.
    try:
        hrefs = await page.locator("a[href]").evaluate_all(
            "els => els.map(a => a.getAttribute('href')).filter(Boolean)"
        )
    except Exception:
        return []
    return [str(h) for h in hrefs if isinstance(h, str)]


async def _extract_shop_all_pl(page: Any) -> list[str]:
    hrefs: list[str] = []
    # common patterns: "Shop All" as a link or button
    for sel in [
        "a:has-text('Shop All')",
        "a:has-text('Shop all')",
        "a[aria-label*='Shop All' i]",
        "a[data-testid*='shop-all' i]",
    ]:
        try:
            nodes = await page.locator(sel).all()
        except Exception:
            nodes = []
        for n in nodes[:20]:
            try:
                h = await n.get_attribute("href")
            except Exception:
                h = None
            if h:
                u = _norm(h)
                if _is_pl(u) and u not in hrefs:
                    hrefs.append(u)
    return hrefs


async def _extract_modules(page: Any) -> list[dict[str, Any]]:
    """
    Heuristic module extraction:
    - Find headings that contain "Shop by" / "Shop By"
    - For each heading, take nearby links (within the same section/container)
    """
    modules: list[dict[str, Any]] = []

    # Find candidate headings
    heading_locator = page.locator(":is(h1,h2,h3,h4,div,span):has-text('Shop by'), :is(h1,h2,h3,h4,div,span):has-text('Shop By')")
    try:
        heading_count = await heading_locator.count()
    except Exception:
        heading_count = 0

    for idx in range(min(heading_count, 25)):
        h = heading_locator.nth(idx)
        try:
            heading_text = (await h.inner_text()).strip()
        except Exception:
            heading_text = "Shop by"

        # Walk up to find a container, then collect links inside it.
        container = h.locator("xpath=ancestor-or-self::*[self::section or self::div][1]")
        try:
            links = await container.locator("a[href]").evaluate_all(
                "els => els.map(a => a.getAttribute('href')).filter(Boolean)"
            )
        except Exception:
            links = []

        pl_links = []
        c_links = []
        for raw in links[:250]:
            u = _norm(str(raw))
            if _is_pl(u):
                if u not in pl_links:
                    pl_links.append(u)
            elif _is_c(u):
                if u not in c_links:
                    c_links.append(u)

        if pl_links or c_links:
            modules.append(
                {
                    "heading": heading_text,
                    "pl_links": pl_links,
                    "c_links": c_links,
                }
            )

    return modules


@dataclass(frozen=True)
class CPageRecord:
    url: str
    shop_all_pl: list[str]
    modules: list[dict[str, Any]]
    direct_pl: list[str]
    direct_c: list[str]


async def main(max_c_pages: int = 600, max_depth: int = 5) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Resume support (best-effort): if outputs exist, continue from previous visited set.
    records: list[dict[str, Any]] = []
    if OUT_RAW.exists():
        try:
            loaded = json.loads(OUT_RAW.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                records = [r for r in loaded if isinstance(r, dict)]
        except Exception:
            records = []
    visited_c: set[str] = set()
    if OUT_C.exists():
        try:
            visited_c = {
                _norm(line)
                for line in OUT_C.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip()
            }
        except Exception:
            visited_c = set()

    def _build_pl_candidates(seed_pl: list[str], recs: list[dict[str, Any]]) -> list[str]:
        pl_candidates: list[str] = []
        pl_candidates.extend(seed_pl)

        for rec in recs:
            if rec.get("type") != "c_page":
                continue
            shop_all_pl = rec.get("shop_all_pl") or []
            if shop_all_pl:
                for u in shop_all_pl:
                    if u not in pl_candidates:
                        pl_candidates.append(u)
                continue

            # No shop all: pick first Shop By module that yields /pl/ links
            modules = rec.get("modules") or []
            chosen = None
            for m in modules:
                pls = m.get("pl_links") or []
                if pls:
                    chosen = pls
                    break
            if chosen:
                for u in chosen:
                    if u not in pl_candidates:
                        pl_candidates.append(u)
        return pl_candidates

    def _checkpoint(seed_pl: list[str]) -> None:
        pl_candidates = _build_pl_candidates(seed_pl, records)
        OUT_RAW.write_text(json.dumps(records, indent=2), encoding="utf-8")
        OUT_PL.write_text("\n".join(pl_candidates) + ("\n" if pl_candidates else ""), encoding="utf-8")
        OUT_C.write_text("\n".join(sorted(visited_c)) + ("\n" if visited_c else ""), encoding="utf-8")

    async with async_playwright() as p:
        async def _launch() -> Any:
            return await p.chromium.launch_persistent_context(
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

        async def _launch_stable_page() -> tuple[Any, Any]:
            last_err: Exception | None = None
            for attempt in range(5):
                context = None
                try:
                    context = await _launch()
                    page = context.pages[0] if context.pages else await context.new_page()
                    # Give Chrome a moment to settle; this avoids occasional immediate TargetClosedError.
                    await asyncio.sleep(1.2 + random.random() * 1.2)
                    await _warmup(page)
                    return context, page
                except Exception as e:
                    last_err = e
                    try:
                        if context is not None:
                            await context.close()
                    except Exception:
                        pass
                    await asyncio.sleep(2 + attempt * 2)
            raise RuntimeError(
                f"Failed to launch a stable Chrome persistent context for discovery (last error: {last_err})."
            )

        context, page = await _launch_stable_page()

        # Start from Departments
        for attempt in range(3):
            try:
                await page.goto(START, wait_until="domcontentloaded", timeout=60000)
                break
            except Exception:
                # If the page/context died, relaunch.
                try:
                    await _warmup(page)
                except Exception:
                    try:
                        await context.close()
                    except Exception:
                        pass
                    context, page = await _launch_stable_page()
                await _human_pause(1200, 2200)
        await _human_pause(1200, 2200)

        dept_hrefs = [_norm(h) for h in await _get_all_hrefs(page)]
        seed_pl = [h for h in dept_hrefs if _is_pl(h)]
        seed_c = [h for h in dept_hrefs if _is_c(h)]

        queue: deque[tuple[str, int]] = deque([(u, 1) for u in seed_c])

        # Add a pseudo-record for the Departments page itself (only once)
        if not any(r.get("type") == "departments_root" and r.get("url") == START for r in records):
            records.append(
            {
                "type": "departments_root",
                "url": START,
                "direct_pl": seed_pl,
                "direct_c": seed_c,
            }
            )
        _checkpoint(seed_pl)

        processed_since_checkpoint = 0

        while queue and len(visited_c) < max_c_pages:
            url, depth = queue.popleft()
            if depth > max_depth:
                continue
            if url in visited_c:
                continue
            visited_c.add(url)

            nav_error = None
            for attempt in range(3):
                try:
                    # Regularly warm up to keep Akamai happy.
                    if attempt > 0 or (len(visited_c) % 25 == 0):
                        try:
                            await _warmup(page)
                        except Exception:
                            try:
                                await context.close()
                            except Exception:
                                pass
                            context, page = await _launch_stable_page()
                        await _human_pause(900, 1600)
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    nav_error = None
                    break
                except Exception as e:
                    nav_error = str(e)
                    await _human_pause(1200, 2200)
            if nav_error:
                records.append(
                    {
                        "type": "c_page_error",
                        "url": url,
                        "depth": depth,
                        "error": nav_error,
                    }
                )
                processed_since_checkpoint += 1
                if processed_since_checkpoint >= 15:
                    _checkpoint(seed_pl)
                    processed_since_checkpoint = 0
                continue
            await _human_pause(900, 1700)
            try:
                await page.mouse.wheel(0, 220 + random.random() * 240)
            except Exception:
                pass
            await _human_pause(700, 1300)

            # Detect obvious blocks
            try:
                title = await page.title()
            except Exception:
                title = ""
            try:
                body_text = await page.locator("body").inner_text(timeout=3000)
            except Exception:
                body_text = ""
            if "Access Denied" in (title or "") or "Access Denied" in (body_text or ""):
                records.append(
                    {
                        "type": "c_page_blocked",
                        "url": url,
                        "depth": depth,
                        "title": title,
                    }
                )
                processed_since_checkpoint += 1
                if processed_since_checkpoint >= 15:
                    _checkpoint(seed_pl)
                    processed_since_checkpoint = 0
                continue

            hrefs = [_norm(h) for h in await _get_all_hrefs(page)]
            direct_pl = []
            direct_c = []
            for h in hrefs:
                if _is_pl(h) and h not in direct_pl:
                    direct_pl.append(h)
                elif _is_c(h) and h not in direct_c:
                    direct_c.append(h)

            shop_all = await _extract_shop_all_pl(page)
            modules = await _extract_modules(page)

            records.append(
                {
                    "type": "c_page",
                    "url": url,
                    "depth": depth,
                    "shop_all_pl": shop_all,
                    "modules": modules,
                    "direct_pl": direct_pl,
                    "direct_c": direct_c,
                }
            )

            # Queue deeper /c/ links
            for cu in direct_c:
                if cu not in visited_c:
                    queue.append((cu, depth + 1))

            processed_since_checkpoint += 1
            if processed_since_checkpoint >= 15:
                _checkpoint(seed_pl)
                processed_since_checkpoint = 0

        _checkpoint(seed_pl)

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
