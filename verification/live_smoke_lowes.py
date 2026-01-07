from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright, Page

ROOT = Path(__file__).resolve().parents[1]
# When executing as `python verification/live_smoke_lowes.py`, Python's import
# root becomes `verification/`, so ensure repo root is on sys.path.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import PARALLEL.scraper as scraper


ARTIFACTS = (ROOT / "verification" / ".artifacts").resolve()
_profile_override = os.getenv("GLOORBOT_LIVE_PROFILE_DIR", "").strip()
PROFILE_DIR = (
    Path(_profile_override).resolve()
    if _profile_override
    else (ROOT / "verification" / ".pw_profile").resolve()
)


MONEY_RE = re.compile(r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?")


def _money_to_float(s: str) -> float | None:
    if not s:
        return None
    m = MONEY_RE.search(s)
    if not m:
        return None
    compact = m.group(0).replace(" ", "").replace(",", "")
    try:
        return float(compact.replace("$", ""))
    except Exception:
        return None


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return s[:80] or "artifact"


async def _warmup_lowes(page: Page) -> dict:
    """
    Best-effort Akamai warmup.

    Lowe's can return HTTP 200 while still being blocked ("Access Denied") and/or
    issue a non-warmed `_abck` cookie. This routine does multiple lightweight
    navigations + a small scroll to encourage a warm session before we attempt
    SKU-level assertions.
    """

    last = {"title": "", "_abck_has_0": False, "warmed": False, "attempts": 0}
    for attempt in range(1, 6):
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2500 + (attempt * 500))
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.25)")
        except Exception:
            pass
        await page.wait_for_timeout(1200)

        title = await page.title()
        cookies = await page.context.cookies()
        abck = ""
        for c in cookies:
            if c.get("name") == "_abck":
                abck = c.get("value") or ""
                break

        warmed = ("~0~" in abck) and ("access denied" not in title.lower())
        last = {
            "title": title,
            "_abck_has_0": "~0~" in abck,
            "warmed": warmed,
            "attempts": attempt,
        }
        if warmed:
            return last

    return last


async def _goto_with_block_retries(page: Page, url: str, *, max_attempts: int = 6) -> dict:
    """
    Navigate with retries for Lowe's Akamai flakiness.

    Lowe's can intermittently return "Access Denied" even after a good warmup.
    This helper retries with lightweight backoff + a short detour to homepage.
    """
    last_title = ""
    for attempt in range(1, max_attempts + 1):
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000 + attempt * 400)
        last_title = await page.title()
        if "access denied" not in last_title.lower():
            return {"ok": True, "attempts": attempt, "title": last_title, "url": page.url}

        # Try a cheap recover: reload, then home, then back.
        try:
            await page.reload(wait_until="domcontentloaded")
        except Exception:
            pass
        await page.wait_for_timeout(1500 + attempt * 400)
        try:
            await page.goto("https://www.lowes.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(1500 + attempt * 400)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.2)")
        except Exception:
            pass

    return {"ok": False, "attempts": max_attempts, "title": last_title, "url": page.url}


async def _extract_plp_tile_prices(page: Page, plp_url: str, sku: str) -> dict: 
    nav = await _goto_with_block_retries(page, plp_url, max_attempts=6)
    await page.wait_for_timeout(1200)
    title = await page.title()
    if not nav.get("ok") or ("access denied" in title.lower()):
        raise RuntimeError("Blocked on PLP (Access Denied)")

    # Give client-side rendering a chance and trigger lazy-load.
    try:
        await page.wait_for_selector("a[href*='/pd/']", timeout=10_000)
    except Exception:
        pass
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.35)")
    except Exception:
        pass
    await page.wait_for_timeout(1500)

    resolved_sku = sku.strip()

    link = None
    if resolved_sku:
        link = page.locator(f"a[href*='{resolved_sku}']").first

    if (link is None) or (await link.count() == 0):
        # Auto-pick a product tile if the requested SKU is absent (inventory changes frequently).
        # Prefer a tile that has the now-price selector so we can do a meaningful DOM truth check.
        candidates = page.locator("a[href*='/pd/']")
        if await candidates.count() == 0:
            raise RuntimeError("Could not find any /pd/ links on PLP")

        picked = None
        for i in range(min(50, await candidates.count())):
            cand = candidates.nth(i)
            cand_tid = await page.evaluate(
                """(el) => {
                  const t = el.closest('[data-tile]');
                  return t ? t.getAttribute('data-tile') : null;
                }""",
                await cand.element_handle(),
            )
            if not cand_tid:
                continue
            scope = page.locator(f"[data-tile='{cand_tid}']")
            has_now = await scope.locator("[data-selector='splp-prd-act-$']").count() > 0
            has_now = has_now or (await scope.locator("[aria-label*='Actual Price']").count() > 0)
            if not has_now:
                continue
            picked = cand
            break

        link = picked or candidates.first
        href = (await link.get_attribute("href")) or ""
        m = re.search(r"/(\d{6,})", href)
        if m:
            resolved_sku = m.group(1)

    # Find the nearest data-tile ancestor, then the tile_group container.
    tid = await page.evaluate(
        """(el) => {
          const t = el.closest('[data-tile]');
          return t ? t.getAttribute('data-tile') : null;
        }""",
        await link.element_handle(),
    )
    scope = None
    if tid:
        scope = page.locator(f"[data-tile='{tid}']")
    else:
        # Fallback to a broader card container when data-tile isn't present.
        scope = link.locator("xpath=ancestor::div[contains(@class,'tile_group')][1]").first
        if await scope.count() == 0:
            scope = link.locator("xpath=ancestor::article[1]").first
        if await scope.count() == 0:
            scope = link.locator("xpath=ancestor::div[1]").first
        if await scope.count() == 0:
            raise RuntimeError("Could not locate a card container for picked /pd/ link")
    prices = await scraper.extract_prices_from_card(scope)

    # Truth directly from DOM nodes inside the tile (best-effort).
    now_aria = await scope.locator("[data-selector='splp-prd-act-$']").first.get_attribute("aria-label")
    now_text = await scope.locator("[data-selector='splp-prd-act-$']").first.inner_text()
    was_aria = await scope.locator("[data-selector='splp-prd-promo-was-$']").first.get_attribute("aria-label")
    was_text = await scope.locator("[data-selector='splp-prd-promo-was-$']").first.inner_text()

    return {
        "sku": resolved_sku,
        "data_tile": tid,
        "picked_href": (await link.get_attribute("href")) if link else "",
        "scraper": prices,
        "plp_title": title,
        "plp_url": page.url,
        "dom": {
            "now_aria": now_aria or "",
            "now_text": now_text or "",
            "was_aria": was_aria or "",
            "was_text": was_text or "",
        },
    }


async def _extract_pdp_prices(page: Page, pdp_url: str) -> dict:
    await page.goto(pdp_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)

    # Lowe's commonly exposes the main price via data-testid="main-price".
    txt = ""
    loc = page.locator("[data-testid='main-price']").first
    if await loc.count() > 0:
        txt = (await loc.inner_text()) or ""

    # Parse "Now" and "Actual price was" if present.
    now = None
    was = None

    # Now: first money in the block.
    m0 = MONEY_RE.search(txt)
    if m0:
        now = _money_to_float(m0.group(0))

    # Was: look for phrase.
    m_was = re.search(r"(?i)actual price was[^$]{0,30}(\$\s*\d[\d,]*(?:\.\d{2})?)", txt)
    if m_was:
        was = _money_to_float(m_was.group(1))

    return {"pdp_url": pdp_url, "text": txt[:1200], "now": now, "was": was}


@dataclass(frozen=True)
class LiveConfig:
    sku: str
    store_number: str
    plp_url: str
    pdp_url: str


async def main_async() -> int:
    # Default target matches the historic bug report.
    cfg = LiveConfig(
        sku=os.getenv("GLOORBOT_LIVE_SKU", "").strip(),
        store_number=os.getenv("GLOORBOT_LIVE_STORE", "1631"),
        plp_url=os.getenv(
            "GLOORBOT_LIVE_PLP",
            "https://www.lowes.com/pl/showers/shower-stalls-enclosures/4294648500?inStock=1&rollUpVariants=0",
        ),
        pdp_url=os.getenv(
            "GLOORBOT_LIVE_PDP",
            "https://www.lowes.com/pd/DreamLine-French-Corner-French-Black-Floor-Square-2-Piece-Corner-Shower-Kit-Actual-74-75-in-x-36-in-x-36-in/1000212195",
        ),
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=os.getenv("GLOORBOT_LIVE_HEADLESS", "0").strip() in {"1", "true", "yes"},
            channel="chrome" if os.getenv("GLOORBOT_BROWSER_CHANNEL", "chrome") == "chrome" else None,
            viewport={"width": 1400, "height": 900},
        )
        page = await ctx.new_page()

        warm = await _warmup_lowes(page)
        await page.screenshot(path=str(ARTIFACTS / f"{ts}_warmup.png"), full_page=True)
        if not warm.get("warmed"):
            out = {"ok": False, "stage": "warmup", "warmup": warm}
            (ARTIFACTS / f"{ts}_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(json.dumps(out, indent=2))
            print(
                "\nBlocked or not warmed. Re-run until `_abck` contains `~0~`.\n"
                "Tip: warm manually in the opened Chrome window, then re-run.",
                file=sys.stderr,
            )
            await ctx.close()
            return 2

        plp_url = cfg.plp_url + (f"&storeNumber={cfg.store_number}" if "storeNumber=" not in cfg.plp_url else "")
        try:
            plp = await _extract_plp_tile_prices(page, plp_url, cfg.sku)
            await page.screenshot(path=str(ARTIFACTS / f"{ts}_plp.png"), full_page=True)
        except Exception as e:
            await page.screenshot(path=str(ARTIFACTS / f"{ts}_plp_fail.png"), full_page=True)
            out = {
                "ok": False,
                "stage": "plp",
                "warmup": warm,
                "plp_url": plp_url,
                "page_url": page.url,
                "title": await page.title(),
                "error": repr(e),
                "artifacts": {
                    "warmup_screenshot": str((ARTIFACTS / f"{ts}_warmup.png").resolve()),
                    "plp_fail_screenshot": str((ARTIFACTS / f"{ts}_plp_fail.png").resolve()),
                },
            }
            (ARTIFACTS / f"{ts}_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(json.dumps(out, indent=2))
            await ctx.close()
            return 2

        pdp_url = cfg.pdp_url
        if plp.get("picked_href"):
            href = plp["picked_href"]
            if isinstance(href, str) and href.startswith("/"):
                pdp_url = "https://www.lowes.com" + href
        pdp_url = pdp_url + (f"?storeNumber={cfg.store_number}" if "storeNumber=" not in pdp_url else "")
        pdp = await _extract_pdp_prices(page, pdp_url)
        await page.screenshot(path=str(ARTIFACTS / f"{ts}_pdp.png"), full_page=True)

        scraper_now = _money_to_float(plp["scraper"].get("price") or "")
        scraper_was = _money_to_float(plp["scraper"].get("was_price") or "")
        dom_now = _money_to_float(plp["dom"].get("now_aria") or plp["dom"].get("now_text") or "")
        dom_was = _money_to_float(plp["dom"].get("was_aria") or plp["dom"].get("was_text") or "")

        def close_enough(a: float | None, b: float | None) -> bool:
            if a is None or b is None:
                return False
            return abs(a - b) <= 0.01

        ok_now = close_enough(scraper_now, dom_now)
        ok_was = (dom_was is None and (scraper_was is None)) or close_enough(scraper_was, dom_was)

        out = {
            "ok": bool(ok_now and ok_was),
            "warmup": warm,
            "plp_url": plp_url,
            "pdp_url": pdp_url,
            "sku": cfg.sku,
            "store_number": cfg.store_number,
            "values": {
                "dom_now": dom_now,
                "dom_was": dom_was,
                "scraper_now": scraper_now,
                "scraper_was": scraper_was,
                "pdp_now": pdp.get("now"),
                "pdp_was": pdp.get("was"),
            },
            "plp_detail": plp,
            "pdp_detail": pdp,
            "artifacts": {
                "warmup_screenshot": str((ARTIFACTS / f"{ts}_warmup.png").resolve()),
                "plp_screenshot": str((ARTIFACTS / f"{ts}_plp.png").resolve()),
                "pdp_screenshot": str((ARTIFACTS / f"{ts}_pdp.png").resolve()),
            },
        }

        (ARTIFACTS / f"{ts}_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))

        await ctx.close()
        return 0 if out["ok"] else 1


def main() -> int:
    if os.getenv("GLOORBOT_LIVE_TEST", "0").strip().lower() not in {"1", "true", "yes"}:
        print(
            "Live smoke test disabled. Set `GLOORBOT_LIVE_TEST=1` to run.\n"
            "Outputs go to `verification/.artifacts/`.\n"
            "Note: Lowe's may block headless automation; run headful if needed:\n"
            "  set GLOORBOT_LIVE_HEADLESS=0",
            flush=True,
        )
        return 0

    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
