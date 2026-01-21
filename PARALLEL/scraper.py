"""
Lowe's Full Catalog Scraper - WA/OR Stores

PROVEN WORKING APPROACH:
✅ Chrome channel (NOT Chromium)
✅ Persistent browser profiles
✅ Homepage warmup with human behavior
✅ NO playwright-stealth (red flag!)
✅ NO fingerprint injection (makes it worse!)

PURPOSE:
Clone entire product catalog from WA/OR Lowe's stores to find local markdowns.
Scrapes "pickup today" products from every department in every store.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import random
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.async_api import async_playwright, Page, Locator


# ============================================================================
# MOCK ACTOR (replaces Apify dependency)
# ============================================================================

class Actor:
    class log:
        @staticmethod
        def info(msg): print(f"[INFO] {msg}")
        @staticmethod
        def warning(msg): print(f"[WARN] {msg}")
        @staticmethod
        def error(msg): print(f"[ERROR] {msg}")


# ============================================================================
# OPTIONAL NAVIGATION LOGGING (used by the installed Worker)
# ============================================================================

def _strip_pagination(url: str) -> str:
    try:
        p = urlparse(url)
        q = parse_qs(p.query, keep_blank_values=True)
        q.pop("offset", None)
        new_query = urlencode(q, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
    except Exception:
        return url


def _navlog(event: str, payload: dict) -> None:
    """
    Best-effort JSONL navigation log.

    Enabled by setting env var `GLOORBOT_NAVLOG_PATH` (worker sets this).
    """
    path = (os.getenv("GLOORBOT_NAVLOG_PATH") or "").strip()
    if not path:
        return
    try:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 10MB rotation, keep a few siblings (best-effort).
        try:
            if out_path.exists() and out_path.stat().st_size >= 10 * 1024 * 1024:
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                rotated = out_path.with_name(f"{out_path.stem}.{ts}{out_path.suffix}")
                try:
                    out_path.rename(rotated)
                except Exception:
                    pass
        except Exception:
            pass

        record = {"ts": datetime.utcnow().isoformat(), "event": event}
        record.update(payload)
        for k in ["requested_url", "landed_url", "url", "page_url", "category_url"]:
            v = record.get(k)
            if isinstance(v, str) and v:
                record[f"{k}_canonical"] = _strip_pagination(v)
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def _is_redirected_to_c(url: str) -> bool:
    return ("/c/" in url) and ("/pl/" not in url)


# ============================================================================
# CONFIG
# ============================================================================

# URLs file should be in the same folder as this script
LOWES_MAP_PATH = Path(__file__).parent / "urls.txt"


# ============================================================================
# LOAD STORES & CATEGORIES
# ============================================================================

def load_stores_and_categories():
    """Load WA/OR stores and all category URLs from LowesMap.txt"""
    stores = []
    categories = []

    if not LOWES_MAP_PATH.exists():
        Actor.log.warning(f"LowesMap.txt not found at {LOWES_MAP_PATH}")
        return stores, categories

    with open(LOWES_MAP_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('This') or line.startswith('##'):
                continue

            # Store URLs
            if '/store/' in line:
                match = re.search(r'/store/([A-Z]{2})-([^/]+)/(\d+)', line)
                if match:
                    state, city, store_id = match.groups()
                    stores.append({
                        "url": line,
                        "store_id": store_id,
                        "city": city.replace('-', ' '),
                        "state": state,
                        "name": f"{city}, {state} (#{store_id})"
                    })

            # Category URLs (skip clearance)
            elif '/pl/' in line and 'the-back-aisle' not in line.lower():
                categories.append(line)

    Actor.log.info(f"Loaded {len(stores)} stores and {len(categories)} categories")
    return stores, categories


# ============================================================================
# HUMAN BEHAVIOR
# ============================================================================

async def human_mouse_move(page: Page):
    """Human-like mouse movement"""
    viewport = page.viewport_size
    width = viewport.get('width', 1440) if viewport else 1440
    height = viewport.get('height', 900) if viewport else 900

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
        await asyncio.sleep((18 + random.random() * 30) / 1000)  # Slightly increased


async def human_scroll(page: Page):
    """Human-like scrolling"""
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep((45 + random.random() * 90) / 1000)  # Slightly increased


async def warmup_session(page: Page):
    """
    CRITICAL: Visit homepage with human behavior to establish trust.
    
    PROVEN WORKING: NO fingerprint injection! (Makes detection WORSE!)
    Just do natural human-like interactions.
    """
    Actor.log.info("Warming up session...")

    # Go to homepage first
    await page.goto("https://www.lowes.com/", wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3.5 + random.random() * 2)  # 3.5-5.5 seconds

    # Human behavior - mouse movement and scrolling
    await human_mouse_move(page)
    await asyncio.sleep(1 + random.random())
    await human_scroll(page)
    await asyncio.sleep(1.5 + random.random() * 1.5)
    
    # 3. Perform a Search (Crucial for trust)
    Actor.log.info("Searching for 'caulk' to establish trust...")
    try:
        search_input = page.locator('input[id*="search"], input[name*="search"], input[aria-label*="search"]').first
        if await search_input.count() > 0:
            await search_input.click()
            await page.keyboard.type("caulk", delay=100)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await asyncio.sleep(3 + random.random() * 2)
            await human_mouse_move(page)
            await human_scroll(page)
        else:
            Actor.log.warning("Search input not found during warmup")
    except Exception as e:
        Actor.log.warning(f"Search warmup failed: {e}")

    Actor.log.info("Warmup complete")


async def set_store_context(page: Page, store_url: str, store_name: str):
    """Set store for pricing/availability"""
    Actor.log.info(f"Setting store: {store_name}")

    await page.goto(store_url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(2 + random.random())

    # Check if already set (sometimes page says "My Store" immediately)
    try:
        if await page.locator("button:has-text('My Store')").is_visible():
            Actor.log.info("Store already set as My Store")
            return True
        header_store = await page.locator("#store-search-link, [data-test='store-search-link']").first.inner_text()
        if store_name.split(',')[0] in header_store:
            Actor.log.info(f"Store verified in header: {header_store}")
            return True
    except:
        pass

    for selector in ["button:has-text('Set Store')", "button:has-text('Set as My Store')"]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click(timeout=8000)
                await asyncio.sleep(2.5)  # Wait for API update
                Actor.log.info(f"Clicked 'Set Store'")
                return True
        except:
            continue

    # Final verification
    try:
        await page.reload(wait_until='domcontentloaded')
        await asyncio.sleep(2)
        if await page.locator("button:has-text('My Store')").is_visible():
            return True
    except:
        pass

    Actor.log.warning("Could not explicitly set store - hoping default cookies work")
    return False


# ============================================================================
# TILE GROUP EXTRACTION (ROW -> PER-PRODUCT)
# ============================================================================

_MONEY_STR_RE = re.compile(r"\$\s*[0-9,]+(?:\.\d{2})?")
_FINANCING_NOISE_RE = re.compile(
    r"(?i)(/mo\b|\bper\s+month\b|\bmonthly\b|\bmonth\b|suggested\s+payments?"
    r"|special\s+financing|buy\s+now|pay\s+later|learn\s+how|when\s+you\s+choose|eligible\s+purchases|protection|plan|warranty|accessory)"
)
_LABEL_ACTUAL_RE = re.compile(r"(?i)\b(actual|now|sale|current)\s*price\b")
_LABEL_WAS_RE = re.compile(r"(?i)\b(was|regular|original)\s*price\b")

_PRICE_DIAG_FALSE_VALUES = {"0", "false", "no", "off", ""}


def _price_diag_enabled() -> bool:
    return os.getenv("GLOORBOT_PRICE_DIAGNOSTICS", "").strip().lower() not in _PRICE_DIAG_FALSE_VALUES


def _price_diag_max_len() -> int:
    try:
        return max(0, min(int(os.getenv("GLOORBOT_PRICE_DIAG_MAXLEN", "800")), 10000))
    except Exception:
        return 800


def _price_diag_path() -> str:
    # Prefer explicit path if provided (worker can set per-slot).
    p = (os.getenv("GLOORBOT_PRICE_DIAG_PATH") or "").strip()
    if p:
        return p
    # Fallback: write next to navlog if configured (keeps artifacts together).
    nav = (os.getenv("GLOORBOT_NAVLOG_PATH") or "").strip()
    if nav:
        try:
            base = Path(nav)
            return str(base.with_suffix(".price_diag.jsonl"))
        except Exception:
            pass
    return ""


def _truncate(s: str, max_len: int) -> str:
    if not s:
        return ""
    if max_len <= 0:
        return ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _price_diag_write(event: dict) -> None:
    if not _price_diag_enabled():
        return
    try:
        path = _price_diag_path()
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Diagnostics must never crash scraping.
        return


def _first_money_str(text: str) -> str:
    if not text:
        return ""
    m = _MONEY_STR_RE.search(text)
    if not m:
        return ""
    return re.sub(r"\s+", "", m.group(0))


def _looks_like_financing_noise(text: str) -> bool:
    if not text:
        return False
    return bool(_FINANCING_NOISE_RE.search(text))


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _money_values_from_text_blob(text: str) -> list[float]:
    if not text:
        return []

    cleaned = text

    # Remove common savings phrases that can masquerade as prices.
    cleaned = re.sub(
        r"(?i)(save|savings|saved)\s*:?\s*\$?\s*[0-9]+(?:\.[0-9]{1,2})?",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\$?\s*[0-9]+(?:\.[0-9]{1,2})?\s*(?:off|%)", " ", cleaned)

    # Remove shipping/threshold phrases that look like prices.
    cleaned = re.sub(
        r"(?i)(orders?|shipping|spend)\s*(?:over)?\s*\$?\s*[0-9]+",
        " ",
        cleaned,
    )

    # Remove financing/monthly-payment dollar amounts (e.g. "$125/mo", "$167 per month").
    cleaned = re.sub(
        r"(?i)\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:/mo\b|per\s+month\b|a\s+month\b|monthly\b)",
        " ",
        cleaned,
    )

    # Remove "credit offer" prices like "$949.99 ... savings ... Learn How".
    cleaned = re.sub(
        r"(?is)\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?.{0,60}?(savings|financing|eligible purchases|learn how|pay later)",
        " ",
        cleaned,
    )

    # Extract money values, normalized.
    compact = re.sub(r"\s+", "", cleaned)
    compact = compact.replace(",", "")
    vals: list[float] = []
    for m in re.finditer(r"\$([0-9]{1,5})(?:\.([0-9]{2}))?", compact):
        whole = m.group(1)
        cents = m.group(2) or "00"
        try:
            v = float(f"{whole}.{cents}")
        except Exception:
            continue
        if v >= 1.0:
            vals.append(v)
    return vals


async def extract_prices_from_card(card: Locator) -> dict[str, str]:
    """
    Extract {price, was_price} from a product card while avoiding common
    false positives like monthly-payment/financing snippets (e.g. "$125/mo").
    """
    diag: dict = {
        "ts": datetime.utcnow().isoformat(),
        "event": "price_extract",
        "price": None,
        "was_price": None,
        "steps": [],
    }

    # Best-effort card identity (forensics).
    try:
        a = card.locator(":scope a[href*='/pd/']").first
        if await a.count() > 0:
            href = (await a.get_attribute("href")) or ""
            diag["product_href"] = href
            if href.startswith("/"):
                diag["product_url"] = "https://www.lowes.com" + href
            elif href.startswith("http"):
                diag["product_url"] = href
    except Exception:
        pass
    try:
        t = card.locator(":scope [data-selector='splp-prd-ttl'], :scope h2, :scope h3").first
        if await t.count() > 0:
            diag["title"] = _truncate((await t.inner_text()) or "", _price_diag_max_len())
    except Exception:
        pass

    price_text = ""
    was_price = ""

    # 0) data-testid Strategy (PROVEN WORKING from CheapSkater)
    # This is the most reliable selector set - use it first
    try:
        # Try current-price first, then regular-price as fallback
        current_price_el = card.locator(":scope [data-testid='current-price'], :scope [data-testid='regular-price']").first
        if await current_price_el.count() > 0:
            aria = (await current_price_el.get_attribute("aria-label")) or ""
            inner = (await current_price_el.inner_text()) or ""
            candidate = _first_money_str(aria) or _first_money_str(inner)
            rejected = []
            if _looks_like_financing_noise(aria):
                rejected.append("financing_noise_in_aria")
            if _looks_like_financing_noise(inner):
                rejected.append("financing_noise_in_text")
            if candidate and not rejected:
                price_text = candidate
                diag["steps"].append({
                    "source": "data_testid_current_price",
                    "ok": True,
                    "candidate": candidate,
                    "aria": _truncate(aria, _price_diag_max_len()),
                    "text": _truncate(inner, _price_diag_max_len()),
                })
            else:
                diag["steps"].append({
                    "source": "data_testid_current_price",
                    "ok": False,
                    "candidate": candidate,
                    "rejected": rejected,
                    "aria": _truncate(aria, _price_diag_max_len()),
                    "text": _truncate(inner, _price_diag_max_len()),
                })
    except Exception:
        pass

    try:
        was_price_el = card.locator(":scope [data-testid='was-price']").first
        if await was_price_el.count() > 0:
            aria = (await was_price_el.get_attribute("aria-label")) or ""
            inner = (await was_price_el.inner_text()) or ""
            candidate = _first_money_str(aria) or _first_money_str(inner)
            rejected = []
            if _looks_like_financing_noise(aria):
                rejected.append("financing_noise_in_aria")
            if _looks_like_financing_noise(inner):
                rejected.append("financing_noise_in_text")
            if candidate and not rejected:
                was_price = candidate
                diag["steps"].append({
                    "source": "data_testid_was_price",
                    "ok": True,
                    "candidate": candidate,
                    "aria": _truncate(aria, _price_diag_max_len()),
                    "text": _truncate(inner, _price_diag_max_len()),
                })
            else:
                diag["steps"].append({
                    "source": "data_testid_was_price",
                    "ok": False,
                    "candidate": candidate,
                    "rejected": rejected,
                    "aria": _truncate(aria, _price_diag_max_len()),
                    "text": _truncate(inner, _price_diag_max_len()),
                })
    except Exception:
        pass

    # 1) Canonical Lowe's data-selector attributes (fallback - only if data-testid didn't work).
    if not price_text:
        try:
            now_el = card.locator(":scope [data-selector='splp-prd-act-$']").first
            diag["canonical_now_count"] = await card.locator(":scope [data-selector='splp-prd-act-$']").count()
            if await now_el.count() > 0:
                aria = (await now_el.get_attribute("aria-label")) or ""
                inner = (await now_el.inner_text()) or ""
                candidate = _first_money_str(aria) or _first_money_str(inner)
                rejected = []
                if _looks_like_financing_noise(aria):
                    rejected.append("financing_noise_in_aria")
                if _looks_like_financing_noise(inner):
                    rejected.append("financing_noise_in_text")
                if candidate and not rejected:
                    price_text = candidate
                    diag["steps"].append(
                        {
                            "source": "canonical_now_selector",
                            "ok": True,
                            "candidate": candidate,
                            "aria": _truncate(aria, _price_diag_max_len()),
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
                else:
                    diag["steps"].append(
                        {
                            "source": "canonical_now_selector",
                            "ok": False,
                            "candidate": candidate,
                            "rejected": rejected,
                            "aria": _truncate(aria, _price_diag_max_len()),
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
        except Exception:
            pass

    if not was_price:
        try:
            was_el = card.locator(":scope [data-selector='splp-prd-promo-was-$']").first
            diag["canonical_was_count"] = await card.locator(":scope [data-selector='splp-prd-promo-was-$']").count()
            if await was_el.count() > 0:
                aria = (await was_el.get_attribute("aria-label")) or ""
                inner = (await was_el.inner_text()) or ""
                candidate = _first_money_str(aria) or _first_money_str(inner)
                rejected = []
                if _looks_like_financing_noise(aria):
                    rejected.append("financing_noise_in_aria")
                if _looks_like_financing_noise(inner):
                    rejected.append("financing_noise_in_text")
                if candidate and not rejected:
                    was_price = candidate
                    diag["steps"].append(
                        {
                            "source": "canonical_was_selector",
                            "ok": True,
                            "candidate": candidate,
                            "aria": _truncate(aria, _price_diag_max_len()),
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
                else:
                    diag["steps"].append(
                        {
                            "source": "canonical_was_selector",
                            "ok": False,
                            "candidate": candidate,
                            "rejected": rejected,
                            "aria": _truncate(aria, _price_diag_max_len()),
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
        except Exception:
            pass

    # 2) Aria-label scanning fallback (covers cards without splp-prd-* data-selectors).
    # Limit work: only scan aria-labels if canonical selectors didn't succeed.
    if (not price_text) or (not was_price):
        try:
            aria_nodes = card.locator(":scope [aria-label]")
            aria_count = await aria_nodes.count()
            diag["aria_label_count"] = aria_count
            n = min(aria_count, 80)
            for i in range(n):
                label = (await aria_nodes.nth(i).get_attribute("aria-label")) or ""
                if not label or "$" not in label:
                    continue
                if _looks_like_financing_noise(label):
                    diag["steps"].append(
                        {
                            "source": "aria_scan",
                            "ok": False,
                            "rejected": ["financing_noise_in_aria"],
                            "aria": _truncate(label, _price_diag_max_len()),
                        }
                    )
                    continue
                money = _first_money_str(label)
                if not money:
                    continue
                if (not price_text) and _LABEL_ACTUAL_RE.search(label):
                    price_text = money
                    diag["steps"].append(
                        {
                            "source": "aria_scan_actual",
                            "ok": True,
                            "candidate": money,
                            "aria": _truncate(label, _price_diag_max_len()),
                        }
                    )
                if (not was_price) and _LABEL_WAS_RE.search(label):
                    was_price = money
                    diag["steps"].append(
                        {
                            "source": "aria_scan_was",
                            "ok": True,
                            "candidate": money,
                            "aria": _truncate(label, _price_diag_max_len()),
                        }
                    )
                if price_text and was_price:
                    break
        except Exception:
            pass

    # 3) Strikethrough fallback for was-price.
    if not was_price:
        try:
            strike = card.locator(":scope s, :scope del").first
            diag["strike_count"] = await card.locator(":scope s, :scope del").count()
            if await strike.count() > 0:
                inner = (await strike.inner_text()) or ""
                candidate = _first_money_str(inner)
                rejected = []
                if _looks_like_financing_noise(inner) or _looks_like_financing_noise(candidate):
                    rejected.append("financing_noise_in_text")
                if candidate and not rejected:
                    was_price = candidate
                    diag["steps"].append(
                        {
                            "source": "strike_was",
                            "ok": True,
                            "candidate": candidate,
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
                else:
                    diag["steps"].append(
                        {
                            "source": "strike_was",
                            "ok": False,
                            "candidate": candidate,
                            "rejected": rejected,
                            "text": _truncate(inner, _price_diag_max_len()),
                        }
                    )
        except Exception:
            pass

    # 4) Last resort: infer from blob, but aggressively remove common noise.
    if (not price_text) or (not was_price):
        try:
            blob = (await card.inner_text()) or ""
            vals = _money_values_from_text_blob(blob)
            if vals:
                candidates = sorted({v for v in vals if v >= 1.0})
                inferred_was = max(candidates) if candidates else None
                inferred_now = None
                if inferred_was is not None:
                    smaller = [v for v in candidates if v < inferred_was]
                    inferred_now = max(smaller) if smaller else None

                # Sanity: prevent impossible matches (e.g., $1000 item = $4)
                if (
                    inferred_was is not None
                    and inferred_was >= 200
                    and inferred_now is not None
                    and inferred_now <= 10
                ):
                    inferred_now = None

                # Only use inference when we can confidently form a pair.
                if inferred_now is not None and inferred_was is not None:
                    if not price_text:
                        price_text = _fmt_money(inferred_now)
                    if not was_price:
                        was_price = _fmt_money(inferred_was)
                    diag["steps"].append(
                        {
                            "source": "blob_infer_pair",
                            "ok": True,
                            "inferred_now": inferred_now,
                            "inferred_was": inferred_was,
                            "text": _truncate(blob, _price_diag_max_len()),
                        }
                    )
            else:
                diag["steps"].append(
                    {
                        "source": "blob_infer_pair",
                        "ok": False,
                        "reason": "no_money_values",
                        "text": _truncate(blob, _price_diag_max_len()),
                    }
                )
        except Exception:
            pass

    out = {
        "price": price_text.strip() if price_text else "N/A",
        "was_price": was_price.strip() if was_price else "",
    }
    diag["price"] = out["price"]
    diag["was_price"] = out["was_price"]
    try:
        diag["card_text"] = _truncate((await card.inner_text()) or "", _price_diag_max_len())
    except Exception:
        pass
    _price_diag_write(diag)
    try:
        # Emit a single-line marker into Actor logs too (cheap to grep in Render).
        if _price_diag_enabled():
            Actor.log.info(f"PRICE_DIAG now={out['price']} was={out['was_price']} steps={len(diag.get('steps') or [])}")
    except Exception:
        pass
    return out


async def extract_tile_group_products(card: Locator) -> list[dict]:
    # Lowe's tile_group rows contain multiple products grouped by data-tile.
    # Split each tile_group into per-product records to avoid mixing prices/titles.
    tile_nodes = card.locator("[data-tile]")
    tile_ids: set[str] = set()
    for i in range(await tile_nodes.count()):
        tid = await tile_nodes.nth(i).get_attribute("data-tile")
        if tid:
            tile_ids.add(tid)

    products: list[dict] = []
    for tid in sorted(tile_ids, key=lambda x: int(x) if str(x).isdigit() else str(x)):
        scope = card.locator(f"[data-tile='{tid}']")
        link_el = scope.locator("a[href*='/pd/']").first
        href = await link_el.get_attribute("href") if await link_el.count() > 0 else ""

        title_text = ""
        title_el = scope.locator("[data-selector='splp-prd-ttl']").first
        if await title_el.count() > 0:
            title_text = (await title_el.inner_text()).strip()
        if not title_text:
            aria = (await link_el.get_attribute("aria-label")) if await link_el.count() > 0 else ""
            title_text = (aria or "").strip()

        prices = await extract_prices_from_card(scope)
        price_text = prices.get("price", "N/A")
        was_price = prices.get("was_price", "")

        image_url = None
        try:
            # Find the actual product image, NOT badge/clearance SVGs
            all_imgs = await scope.locator("img").all()
            for img in all_imgs:
                src = (
                    await img.get_attribute("src")
                    or await img.get_attribute("data-src")
                    or await img.get_attribute("data-lazy-src")
                    or ""
                )
                if not src:
                    srcset = (
                        await img.get_attribute("srcset")
                        or await img.get_attribute("data-srcset")
                        or ""
                    )
                    first = srcset.split(",")[0].strip()
                    src = first.split(" ")[0].strip() if first else ""
                
                # Skip badge/clearance SVGs (including the specific clearance.svg badge)
                if "/badges/" in src or src.endswith(".svg") or "clearance.svg" in src:
                    continue
                # Skip data: URIs
                if src.startswith("data:"):
                    continue
                
                if src.startswith("//"):
                    src = "https:" + src
                if src.startswith("/"):
                    src = "https://www.lowes.com" + src
                
                # Prefer product images from mobileimages.lowes.com/productimages/
                if "productimages/" in src or "mobileimages.lowes.com" in src:
                    image_url = src
                    break  # Found the best match
                
                # Fallback: any non-badge image with jpg/png extension
                if not image_url and (".jpg" in src.lower() or ".png" in src.lower() or ".jpeg" in src.lower()):
                    image_url = src
        except Exception:
            image_url = None

        if not href or not title_text or "$" in title_text or "%" in title_text:
            continue

        products.append(
            {
                "title": title_text.strip(),
                "price": price_text.strip() if price_text else "N/A",
                "was_price": was_price.strip() if was_price else "",
                "image_url": image_url,
                "has_markdown": bool(was_price),
                "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
            }
        )

    return products


# ============================================================================
# PICKUP FILTER - CRITICAL FOR LOCAL INVENTORY
# ============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """
    Apply the pickup filter with VERIFICATION and AVAILABILITY CHECK.

    This is the most critical function - without the pickup filter,
    we get inventory for ALL stores, not just local availability.

    IMPORTANT FIX: Now checks if the pickup filter is DISABLED (greyed out).
    When a store has no pickup items in a category, the filter button is disabled.
    Previously, the scraper would continue scraping empty/wrong results.
    Now it detects disabled filters and skips the category entirely.

    Returns:
        True: Filter was successfully applied and verified
        False: Filter is disabled/unavailable OR cannot be applied - SKIP CATEGORY
    """
    print(f"[DEBUG] Applying Pickup Filter for {category_name}", flush=True)

    # Selectors for pickup filter elements (comprehensive list)
    # CRITICAL: The actual Lowe's UI shows "Pickup Today at:" with checkbox
    pickup_selectors = [
        # THE ACTUAL LOWE'S CHECKBOX - most important
        'label:has-text("Pickup Today at")',
        'label:has-text("Pickup Today")',
        'label:has-text("Pick Up Today")',
        'label:has-text("Free Store Pickup")',
        # Specific selectors that MUST contain pickup in the name/id
        'input[type="checkbox"][id*="Pickup"]',
        'input[type="checkbox"][id*="pickup"]',
        'input[type="checkbox"][name*="pickup"]',
        # Aria labels are very reliable
        '[aria-label*="Pickup" i]',
        # Data test IDs
        '[data-testid*="pickup" i]',
        '[data-test-id*="pickup" i]',
    ]

    # Toggles that might need expanding first
    availability_toggles = [
        'button:has-text("Pickup & Delivery")',
        'summary:has-text("Pickup & Delivery")',
        'button:has-text("Availability")',
        'button:has-text("Get It Fast")',
        'summary:has-text("Availability")',
        'summary:has-text("Get It Fast")',
    ]

    async def expand_availability_section():
        """Expand the availability filter section if collapsed."""
        for toggle_sel in availability_toggles:
            try:
                toggle = page.locator(toggle_sel).first
                if await toggle.count() > 0 and await toggle.is_visible():
                    expanded = await toggle.get_attribute("aria-expanded")
                    if expanded == "false":
                        Actor.log.info(f"[{category_name}] Expanding availability section")
                        await toggle.click()
                        await asyncio.sleep(0.4 + random.random() * 0.4)
                    return True
            except Exception:
                continue
        return False

    async def is_element_disabled(element) -> bool:
        """Check if an element is disabled or greyed out."""
        try:
            # Check disabled attribute
            disabled = await element.get_attribute("disabled")
            if disabled is not None:
                return True

            # Check aria-disabled
            aria_disabled = await element.get_attribute("aria-disabled")
            if aria_disabled == "true":
                return True

            # Check if element or parent has disabled/greyed CSS classes
            class_name = await element.get_attribute("class") or ""
            if any(cls in class_name.lower() for cls in ["disabled", "greyed", "inactive", "unavailable"]):
                return True

            # Check if input checkbox is disabled
            try:
                is_disabled = await element.is_disabled()
                if is_disabled:
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    async def is_filter_selected(el) -> bool:
        """Check if filter element is in selected state."""
        try:
            for attr in ["aria-checked", "aria-pressed", "aria-selected"]:
                val = await el.get_attribute(attr)
                if val == "true":
                    return True
            try:
                return await el.is_checked()
            except Exception:
                return False
        except Exception:
            return False

    # Wait for page to settle
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    await asyncio.sleep(0.3 + random.random() * 0.3)

    # Scroll to top to ensure filter is visible
    try:
        await page.evaluate("window.scrollTo(0, 0)")
    except Exception:
        pass
    await asyncio.sleep(0.2)

    # Try to expand availability section
    await expand_availability_section()

    # APPROACH 1: Try JavaScript-based click on the "Pickup Today at" checkbox
    # This is the most reliable for Lowe's current UI
    async def try_js_checkbox_click():
        """
        Use JavaScript to find and click the pickup checkbox.

        Returns:
            True: Filter successfully applied/verified
            False: Filter not found or error occurred (continue to fallback)
            'disabled': Filter is disabled (no pickup items available - SKIP CATEGORY)
        """
        try:
            result = await page.evaluate("""
                () => {
                    // AGGRESSIVE: Check for disabled state FIRST before trying anything else
                    // Look for the pickup label/checkbox elements

                    // Method 1: Direct XPath search for "Pickup Today at" text
                    const pickupElements = document.evaluate(
                        "//*[contains(text(), 'Pickup Today')]",
                        document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                    );

                    for (let i = 0; i < pickupElements.snapshotLength; i++) {
                        const el = pickupElements.snapshotItem(i);
                        const container = el.closest('div, label, li, fieldset');

                        if (!container) continue;

                        // Check if parent container is disabled
                        const computedStyle = window.getComputedStyle(container);
                        const opacity = computedStyle.opacity;
                        const color = computedStyle.color;

                        // Check for disabled attributes/classes on container or parents
                        let current = container;
                        while (current && current !== document.body) {
                            if (current.hasAttribute('disabled') ||
                                current.getAttribute('aria-disabled') === 'true' ||
                                current.classList.contains('disabled') ||
                                current.classList.contains('greyed') ||
                                current.classList.contains('is-disabled') ||
                                current.getAttribute('data-disabled') === 'true') {
                                return {clicked: false, wasChecked: false, disabled: true, reason: 'parent-disabled'};
                            }
                            current = current.parentElement;
                        }

                        // Check if visually greyed out (low opacity or grey color)
                        if (opacity && parseFloat(opacity) < 0.5) {
                            return {clicked: false, wasChecked: false, disabled: true, reason: 'low-opacity'};
                        }

                        // Look for checkbox in container
                        const cb = container.querySelector('input[type="checkbox"]');
                        if (cb && (cb.disabled || cb.hasAttribute('disabled'))) {
                            return {clicked: false, wasChecked: false, disabled: true, reason: 'checkbox-disabled'};
                        }
                    }

                    // Method 2: Find by checkbox with "Pickup Today" text nearby
                    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                    for (const cb of checkboxes) {
                        // Check if the checkbox is disabled
                        if (cb.disabled || cb.hasAttribute('disabled')) continue;

                        const label = cb.closest('label');
                        if (label && /Pickup Today/i.test(label.innerText)) {
                            // Verify label is not too large (avoids sidebar-wide labels)
                            if (label.innerText.length > 100) continue;

                            // Check parent tree for disabled state
                            let current = label;
                            let isDisabled = false;
                            while (current && current !== document.body) {
                                if (current.hasAttribute('disabled') ||
                                    current.getAttribute('aria-disabled') === 'true' ||
                                    current.classList.contains('disabled') ||
                                    current.classList.contains('greyed')) {
                                    isDisabled = true;
                                    break;
                                }
                                current = current.parentElement;
                            }
                            if (isDisabled) continue;

                            if (!cb.checked) {
                                cb.click();
                                return {clicked: true, wasChecked: false, method: 'label-wrap'};
                            } else {
                                return {clicked: false, wasChecked: true};
                            }
                        }

                        // Also check for label[for] associations
                        if (cb.id) {
                            const labelFor = document.querySelector(`label[for="${cb.id}"]`);
                            if (labelFor && /Pickup Today/i.test(labelFor.innerText)) {
                                if (!cb.checked) {
                                    cb.click();
                                    return {clicked: true, wasChecked: false, method: 'label-for'};
                                } else {
                                    return {clicked: false, wasChecked: true};
                                }
                            }
                        }
                    }

                    return {clicked: false, wasChecked: false, notFound: true};
                }
            """)

            # Check if the filter is disabled (no items available for pickup)
            if result.get('disabled'):
                reason = result.get('reason', 'unknown')
                Actor.log.info(f"[{category_name}] Pickup filter is DISABLED (reason: {reason}) - no pickup items available at this store - SKIPPING CATEGORY")
                return 'disabled'  # Special return value to indicate we should skip

            if result.get('wasChecked'):
                Actor.log.info(f"[{category_name}] Pickup filter already checked (JS)")
                return True
            if result.get('clicked'):
                Actor.log.info(f"[{category_name}] Clicked pickup filter via JS (method: {result.get('method', 'checkbox')})")
                await asyncio.sleep(1.5 + random.random())
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
                # CRITICAL FIX: Verify via URL change - Lowe's uses inStock=1 parameter
                current_url = page.url.lower()
                if "instock=1" in current_url or "pickup" in current_url or "refinement" in current_url:
                    Actor.log.info(f"[{category_name}] Pickup filter verified via URL (inStock param)")
                    return True
                # Even if URL doesn't show it, the click happened - trust it
                Actor.log.info(f"[{category_name}] Pickup filter applied (JS click succeeded)")
                return True

        except Exception as e:
            Actor.log.warning(f"[{category_name}] JS checkbox approach failed: {e}")
        return False

    # Try JS approach first (most reliable)
    js_result = await try_js_checkbox_click()
    if js_result is True:
        # Verify the filter actually shows products
        await asyncio.sleep(2)
        zero_products = await page.evaluate("() => document.body.innerText.match(/0 Products|0 results|Please reduce your filters/i) !== null")
        if zero_products:
            Actor.log.warning(f"[{category_name}] Pickup filter applied but shows 0 products - no pickup items available")
            return False
        return True  # Filter successfully applied with products
    elif js_result == 'disabled':
        Actor.log.info(f"[{category_name}] JS detection confirmed pickup filter is DISABLED - skipping category")
        return False  # Filter is disabled - do NOT attempt fallback
    # If js_result is False (not found), continue to fallback selector-based approach

    # APPROACH 2: Fallback to selector-based clicking
    for attempt in range(3):
        Actor.log.info(f"[{category_name}] Looking for pickup filter via selectors (attempt {attempt + 1}/3)")

        for selector in pickup_selectors:
            try:
                elements = await page.locator(selector).all()

                for element in elements:
                    try:
                        visible = await element.is_visible()
                        if not visible:
                            continue

                        # CRITICAL: Check if element is disabled before attempting to click
                        if await is_element_disabled(element):
                            Actor.log.info(f"[{category_name}] Pickup filter is DISABLED (no pickup items available) - skipping category")
                            return False

                        # STRICT VALIDATION: Element or its title/aria-label must contain "Pickup"
                        text = (await element.inner_text()) or ""
                        aria = (await element.get_attribute("aria-label")) or ""
                        title_attr = (await element.get_attribute("title")) or ""
                        combined_text = (text + " " + aria + " " + title_attr).lower()

                        if "pickup" not in combined_text and "pick up" not in combined_text:
                            # CRITICAL FIX: Check ONLY the immediate parent row, not the whole sidebar
                            # Using specialized Lowe's filter row selectors
                            container_text = await page.evaluate("""(el) => {
                                const row = el.closest('div.filter-label, li.filter-item, div[class*="filter"]');
                                return row ? row.innerText : '';
                            }""", element)
                            
                            if "pickup" not in container_text.lower() and "pick up" not in container_text.lower():
                                Actor.log.debug(f"[{category_name}] Skipping non-pickup filter: '{text[:20]}...' (Container: '{container_text[:30]}')")
                                continue

                        # Skip if text is too long (probably wrong element)
                        if len(text) > 100:
                            continue

                        # Check if already selected
                        if await is_filter_selected(element):
                            Actor.log.info(f"[{category_name}] Pickup filter already active")
                            # Verify it shows products
                            await asyncio.sleep(1)
                            zero_products = await page.locator('text="0 Products"').count() > 0 or await page.locator('text="0 results"').count() > 0
                            if zero_products:
                                Actor.log.warning(f"[{category_name}] Pickup filter active but shows 0 products")
                                return False
                            return True

                        # Click the filter
                        Actor.log.info(f"[{category_name}] Clicking pickup filter: '{text[:40]}'")
                        await element.click()

                        # Wait for page update
                        await asyncio.sleep(0.8 + random.random() * 0.7)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass

                        # Check if we got 0 products after clicking
                        zero_products = await page.locator('text="0 Products"').count() > 0 or await page.locator('text="0 results"').count() > 0
                        if zero_products:
                            Actor.log.warning(f"[{category_name}] Filter click resulted in 0 products - no pickup items available")
                            return False

                        # VERIFY the click worked
                        if await is_filter_selected(element):
                            Actor.log.info(f"[{category_name}] Pickup filter VERIFIED")
                            return True

                        # Check URL for filter params
                        current_url = page.url.lower()
                        if "pickup" in current_url or "availability" in current_url or "refinement" in current_url:
                            Actor.log.info(f"[{category_name}] Pickup filter verified via URL")
                            return True

                    except Exception as e:
                        continue

            except Exception as e:
                continue

        # Wait before retry
        await asyncio.sleep(0.5 + random.random() * 0.5)

    Actor.log.warning(f"[{category_name}] Pickup filter NOT applied after all attempts")
    return False


# ============================================================================
# SCRAPING
# ============================================================================

async def scrape_category_page(page: Page, url: str, store_info: dict, page_num: int = 1) -> list[dict]:
    """Scrape one page of products"""
    products = []

    # Build URL with pagination - preserve all existing query params (including filters!)
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Add/update offset for pagination
    if page_num > 1:
        params['offset'] = [str((page_num - 1) * 24)]
    elif 'offset' in params:
        del params['offset']  # Remove offset for page 1
    
    # Rebuild URL with all params
    new_query = urlencode(params, doseq=True)
    page_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    # Navigate with human behavior - MINIMUM 1.5 seconds to avoid blocking
    await asyncio.sleep(1.5 + random.random() * 2.4)  # 1.5-3.9 seconds (30% inc)

    try:
        await page.goto(page_url, wait_until='domcontentloaded', timeout=60000)
    except asyncio.TimeoutError:
        Actor.log.error(f"Navigation timeout on page {page_num} after 60s")
        raise  # Re-raise timeout - browser might be hung
    except Exception as e:
        Actor.log.error(f"Navigation error on page {page_num}: {e}")
        # If browser connection is broken, don't try to continue
        if "closed" in str(e).lower() or "connection" in str(e).lower():
            raise  # Re-raise to stop category scraping
        return []  # Otherwise just skip this page

    # If pagination navigation got redirected to a /c/ page, abort the category.
    if _is_redirected_to_c(page.url):
        _navlog(
            "redirect_to_c",
            {
                "store_id": store_info.get("store_id"),
                "store_name": store_info.get("name"),
                "requested_url": page_url,
                "landed_url": page.url,
                "page_num": page_num,
            },
        )
        raise RuntimeError(f"Category redirected from /pl/ to /c/ page: {page.url}")

    await asyncio.sleep(2.0 + random.random() * 2.55)  # 2.0-4.55 seconds (30% inc) after page load

    try:
        await human_mouse_move(page)
        await human_scroll(page)
    except Exception as e:
        Actor.log.warning(f"Interaction error on page {page_num}: {e}")
        # Continue even if mouse/scroll fails

    await asyncio.sleep(1.5 + random.random() * 1.75)  # 1.5-3.25 seconds (30% inc) before scraping

    # CRITICAL: Verify the URL still has pickup filter applied.
    # The pickup filter adds parameters like inStock=1 or refinement IDs.
    # If these are missing, we might be scraping unfiltered nationwide inventory.
    current_url_lower = page.url.lower()
    has_pickup_indicator = (
        "instock=1" in current_url_lower or
        "pickup" in current_url_lower or
        "refinement" in current_url_lower
    )
    if not has_pickup_indicator and page_num == 1:
        # On page 1, the filter should definitely be applied.
        # Log a warning but continue - the main grid scoping should still help.
        Actor.log.warning(
            f"[{store_info['name']}] Page {page_num} URL missing pickup filter indicators. "
            f"Results may include non-local inventory. URL: {page.url[:150]}"
        )

    # Check for blocking with timeout
    try:
        title = await asyncio.wait_for(page.title(), timeout=10.0)
        if "Access Denied" in title or "Robot" in title or "Blocked" in title:
            Actor.log.error(f"BLOCKED on page {page_num}: {title}")
            raise Exception(f"Blocked by anti-bot: {title}")  # Raise to stop scraping
        
        # ABSOLUTE KILL-SWITCH: If page says 0 results, STOP IMMEDIATELY
        # This prevents infinite loops on bad filter landing pages
        empty_check = await page.evaluate("""() => {
            const body = document.body.innerText;
            return /0 Products/i.test(body) || /0 results/i.test(body) || /Please reduce your filters/i.test(body);
        }""")
        if empty_check:
            Actor.log.warning(f"[{store_info['name']} - {url.split('/')[-1]}] Zero products detected - ABORTING CATEGORY")
            return []
            
    except asyncio.TimeoutError:
        Actor.log.error(f"Timeout getting page title on page {page_num} - browser may be hung")
        raise  # Re-raise - this indicates a serious problem

    # ------------------------------------------------------------------------
    # Prefer a DOM-scoped extraction for the "Near Me" product list.
    #
    # Why: the page includes multiple non-local sections ("Save Now Storewide",
    # "You May Also Like", etc.) that can pollute results with unrelated products
    # and nonsensical prices (e.g. ads / carousels). We only want the local,
    # pickup-filtered list.
    # ------------------------------------------------------------------------
    expected_tiles = None
    try:
        total_attr = await page.locator("#listItems").first.get_attribute("data-totaltile")
        if total_attr and total_attr.strip().isdigit():
            expected_tiles = int(total_attr.strip())
    except Exception:
        expected_tiles = None

    # Some pages lazily render tiles; do a gentle scroll pass to encourage all
    # items to hydrate before we read the DOM.
    try:
        if expected_tiles and expected_tiles > 3:
            for _ in range(6):
                await page.mouse.wheel(0, 900)
                await asyncio.sleep(0.35 + random.random() * 0.25)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.6 + random.random() * 0.4)
    except Exception:
        pass

    try:
        near_me_payload = await page.evaluate(
            """
            () => {
                function normText(t) {
                    return (t || "").replace(/\\s+/g, " ").trim();
                }

                function firstMoney(t) {
                    const m = String(t || "").match(/\\$\\s*\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?/);
                    return m ? m[0].replace(/\\s+/g, "") : null;
                }

                function normalizeHref(href) {
                    if (!href) return null;
                    if (href.startsWith("/")) return "https://www.lowes.com" + href;
                    if (href.startsWith("http")) return href;
                    return href;
                }

                function extractCard(card) {
                    const a = card.querySelector('a[href*="/pd/"]');
                    const href = normalizeHref(a && a.getAttribute("href"));
                    if (!href) return null;

                    const titleEl =
                        card.querySelector('[data-selector="splp-prd-ttl"]') ||
                        card.querySelector('[data-testid="item-description"]') ||
                        card.querySelector('a[data-testid="item-description-link"]') ||
                        card.querySelector("h3") ||
                        card.querySelector("h2") ||
                        a;
                    let title = normText(titleEl && titleEl.textContent);

                    // Reject obvious non-product titles.
                    const lowTitle = (title || "").toLowerCase();
                    if (!title || title.length < 5) return null;
                    if (lowTitle.includes("you may also like")) return null;
                    if (lowTitle.includes("previously viewed")) return null;
                    if (lowTitle.includes("related products")) return null;
                    if (lowTitle.includes("related searches")) return null;
                    if (lowTitle.includes("pickup today at")) return null;

                    const nowEl = card.querySelector('[data-selector="splp-prd-act-$"]');
                    const wasEl = card.querySelector('[data-selector="splp-prd-promo-was-$"]');
                    const strike = card.querySelector("s, del");

                    const text = normText(card.textContent);
                    const pickupMatch = /pickup\\b/i.test(text) ? (text.match(/pickup[^.]{0,80}/i) || [])[0] : null;

                    // FIX: Make pickup text optional - we already filter by inStock=1 in URL
                    // The pickup filter parameter ensures local inventory
                    // Keeping this check would reject valid products that don't show "pickup" text
                    // if (!pickupMatch) return null;  // REMOVED - too restrictive

                    // FIX: Use aria-label first (contains clean price like "Actual Price $1,597.99")
                    // Only fallback to textContent if aria-label fails
                    let now = null;
                    if (nowEl) {
                        const ariaLabel = nowEl.getAttribute("aria-label") || "";
                        now = firstMoney(ariaLabel) || firstMoney(nowEl.textContent);
                    }
                    // DO NOT fallback to firstMoney(text) - it grabs random $ amounts from card!

                    let was = null;
                    if (wasEl) {
                        const wasAriaLabel = wasEl.getAttribute("aria-label") || "";
                        was = firstMoney(wasAriaLabel) || firstMoney(wasEl.textContent);
                    } else if (strike) {
                        was = firstMoney(strike.textContent);
                    }

                    let imageUrl = null;
                    const img = card.querySelector("img");
                    if (img) {
                        let src = img.getAttribute("src") || img.getAttribute("data-src") || "";
                        if (!src) {
                            const srcset = img.getAttribute("srcset") || img.getAttribute("data-srcset") || "";
                            const first = srcset.split(",")[0].trim();
                            src = first ? first.split(" ")[0].trim() : "";
                        }
                        if (src.startsWith("//")) src = "https:" + src;
                        if (src.startsWith("/")) src = "https://www.lowes.com" + src;
                        if (src.startsWith("data:")) src = "";
                        imageUrl = src || null;
                    }

                    return {
                        href,
                        title,
                        now_price: now,
                        was_price: was,
                        pickup: pickupMatch,
                        image_url: imageUrl,
                    };
                }

                // FIX: Make "Near Me" heading optional - use main grid container as fallback
                // The heading structure changes frequently, but the main grid is stable
                const hCandidates = Array.from(document.querySelectorAll("h1,h2,h3"));
                const nearMeHeading = hCandidates.find((h) => (h.textContent || "").toLowerCase().includes("near me"));
                
                // Find the main product grid container (more reliable than heading)
                const mainGrid = document.querySelector('[data-selector="splp-prd-lst"]') || 
                                 document.querySelector('#listingPagesSearchResults') ||
                                 document.querySelector('.search-results-wrapper') ||
                                 document.querySelector('main');
                
                if (!nearMeHeading && !mainGrid) {
                    return { ok: false, reason: "no_product_container_found", products: [] };
                }

                // Determine the search scope
                let searchScope;
                let debugInfo = [];
                
                if (nearMeHeading) {
                    // Use heading-based scoping if available
                    const allH = Array.from(document.querySelectorAll("h1,h2,h3,h4"));
                    const boundaryHeading =
                        allH.find((h) => (h.textContent || "").toLowerCase().includes("save now storewide")) ||
                        allH.find((h) => (h.textContent || "").toLowerCase().includes("you may also like")) ||
                        allH.find((h) => (h.textContent || "").toLowerCase().includes("previously viewed")) ||
                        null;

                    const range = document.createRange();
                    range.setStartBefore(nearMeHeading);
                    if (boundaryHeading) range.setEndBefore(boundaryHeading);
                    else range.setEndAfter(document.body);

                    const fragment = range.cloneContents();
                    const tmp = document.createElement("div");
                    tmp.appendChild(fragment);
                    searchScope = tmp;
                    debugInfo.push("Using heading-based scope");
                } else {
                    // Use main grid container directly
                    searchScope = mainGrid;
                    debugInfo.push("Using main grid container");
                }

                // IMPORTANT: div.tile_group can contain MULTIPLE products. If we treat it as one
                // card, we can mix href/title from one tile with prices from another tile.
                // This is the root cause of "Product $1000 shows as $10/$125/$131" style bugs.
                function extractTileGroupProducts(tileGroup) {
                    const tileIds = Array.from(
                        new Set(
                            Array.from(tileGroup.querySelectorAll("[data-tile]"))
                                .map((n) => n.getAttribute("data-tile"))
                                .filter((v) => v && v !== "null")
                        )
                    );
                    // Only fall back to the legacy extractor if there are NO data-tile
                    // attributes at all. Even a single tile id can be split across many
                    // nodes, and the data-tile scoped extraction avoids mixing.
                    if (tileIds.length === 0) {
                        const single = extractCard(tileGroup);
                        return single ? [single] : [];
                    }

                    const out = [];
                    for (const tid of tileIds) {
                        const scopeSel = `[data-tile="${tid}"]`;
                        const a = tileGroup.querySelector(`${scopeSel} a[href*="/pd/"]`);
                        const href = normalizeHref(a && a.getAttribute("href"));
                        if (!href) continue;

                        const titleEl =
                            tileGroup.querySelector(`${scopeSel} [data-selector="splp-prd-ttl"]`) ||
                            tileGroup.querySelector(`${scopeSel} [data-testid="item-description"]`) ||
                            tileGroup.querySelector(`${scopeSel} a[data-testid="item-description-link"]`) ||
                            tileGroup.querySelector(`${scopeSel} h3`) ||
                            tileGroup.querySelector(`${scopeSel} h2`) ||
                            a;
                        let title = normText(titleEl && titleEl.textContent);

                        // Reject obvious non-product titles.
                        const lowTitle = (title || "").toLowerCase();
                        if (!title || title.length < 5) continue;
                        if (lowTitle.includes("you may also like")) continue;
                        if (lowTitle.includes("previously viewed")) continue;
                        if (lowTitle.includes("related products")) continue;
                        if (lowTitle.includes("related searches")) continue;
                        if (lowTitle.includes("pickup today at")) continue;

                        const nowEl = tileGroup.querySelector(`${scopeSel} [data-selector="splp-prd-act-$"]`);
                        const wasEl = tileGroup.querySelector(`${scopeSel} [data-selector="splp-prd-promo-was-$"]`);
                        const strike = tileGroup.querySelector(`${scopeSel} s, ${scopeSel} del`);

                        // Build a tile-scoped text blob (avoid mixing across tiles).
                        const tileText = normText(
                            Array.from(tileGroup.querySelectorAll(scopeSel))
                                .map((n) => n.textContent || "")
                                .join(" ")
                        );
                        const pickupMatch = /pickup\b/i.test(tileText)
                            ? (tileText.match(/pickup[^.]{0,80}/i) || [])[0]
                            : null;

                        let now = null;
                        if (nowEl) {
                            const ariaLabel = nowEl.getAttribute("aria-label") || "";
                            now = firstMoney(ariaLabel) || firstMoney(nowEl.textContent);
                        }

                        let was = null;
                        if (wasEl) {
                            const wasAriaLabel = wasEl.getAttribute("aria-label") || "";
                            was = firstMoney(wasAriaLabel) || firstMoney(wasEl.textContent);
                        } else if (strike) {
                            was = firstMoney(strike.textContent);
                        }

                        let imageUrl = null;
                        const img = tileGroup.querySelector(`${scopeSel} img`);
                        if (img) {
                            let src = img.getAttribute("src") || img.getAttribute("data-src") || "";
                            if (!src) {
                                const srcset = img.getAttribute("srcset") || img.getAttribute("data-srcset") || "";
                                const first = srcset.split(",")[0].trim();
                                src = first ? first.split(" ")[0].trim() : "";
                            }
                            if (src.startsWith("//")) src = "https:" + src;
                            if (src.startsWith("/")) src = "https://www.lowes.com" + src;
                            if (src.startsWith("data:")) src = "";
                            imageUrl = src || null;
                        }

                        out.push({
                            href,
                            title,
                            now_price: now,
                            was_price: was,
                            pickup: pickupMatch,
                            image_url: imageUrl,
                        });
                    }

                    return out;
                }

                const cards = Array.from(searchScope.querySelectorAll("div.tile_group"));
                debugInfo.push(`Found ${cards.length} tile_group elements`);
                
                const out = [];
                const seen = new Set();
                let rejectedCount = 0;
                let duplicateCount = 0;
                
                for (const c of cards) {
                    const ps = extractTileGroupProducts(c);
                    if (!ps || ps.length === 0) {
                        rejectedCount++;
                        continue;
                    }
                    for (const p of ps) {
                        if (!p) continue;
                        if (seen.has(p.href)) {
                            duplicateCount++;
                            continue;
                        }
                        seen.add(p.href);
                        out.push(p);
                    }
                }

                debugInfo.push(`Rejected: ${rejectedCount}, Duplicates: ${duplicateCount}, Final: ${out.length}`);
                
                return { 
                    ok: true, 
                    products: out, 
                    method: nearMeHeading ? "heading" : "grid", 
                    cardCount: cards.length,
                    debug: debugInfo.join(" | ")
                };
            }
            """
        )

        # Log debug info from JavaScript extraction
        if isinstance(near_me_payload, dict):
            if not near_me_payload.get("ok"):
                reason = near_me_payload.get("reason", "unknown")
                Actor.log.warning(f"Near-me extraction failed: {reason}")

        if isinstance(near_me_payload, dict) and near_me_payload.get("ok") and near_me_payload.get("products"):
            now = datetime.utcnow().isoformat()
            js_products = near_me_payload.get("products", [])
            
            for idx, p in enumerate(js_products):
                try:
                    product_url = p.get("href")
                    title_text = (p.get("title") or "").strip()
                    price_text = (p.get("now_price") or "").strip()
                    was_price_text = (p.get("was_price") or "").strip()
                    
                    if not product_url or not title_text:
                        continue

                    products.append(
                        {
                            "title": title_text,
                            "price": price_text if price_text else "N/A",
                            "was_price": was_price_text if was_price_text else "",
                            "image_url": p.get("image_url"),
                            "has_markdown": bool(was_price_text),
                            "url": product_url,
                            "category_url": url,
                            "store_id": store_info["store_id"],
                            "store_name": store_info["name"],
                            "store_city": store_info.get("city", ""),
                            "store_state": store_info.get("state", ""),
                            "scraped_at": now,
                        }
                    )
                except Exception as e:
                    Actor.log.warning(f"Product {idx+1}: Exception during processing: {e}")
                    continue

            if expected_tiles and len(products) != expected_tiles:
                Actor.log.warning(
                    f"[{store_info['name']}] Near-me DOM extraction returned {len(products)} items, "
                    f"expected {expected_tiles} (data-totaltile)."
                )

            if products:
                return products
    except Exception as e:
        Actor.log.warning(f"Near-me DOM extraction failed on page {page_num}: {e}")

    # Find product cards with timeout
    # CRITICAL: Lowe's uses div.tile_group for the actual product container with content
    # The data-selector="splp-prd-crd" elements are empty wrappers
    #
    # IMPORTANT: We MUST scope our search to the MAIN PRODUCT GRID only.
    # Lowe's pages have promotional carousels ("Save Now Storewide", "Recommended Products")
    # at the bottom that are NOT filtered by the pickup filter and show nationwide prices.
    # These carousels would pollute our results with wrong prices and store associations.
    #
    # The main product grid is inside: #listingPagesSearchResults, .search-results-wrapper,
    # or sections with role="main" / id="main-content"
    main_grid_containers = [
        '#listingPagesSearchResults',           # Primary Lowe's search results container
        '[data-selector="splp-prd-lst"]',        # Product list container
        '.search-results-wrapper',               # Search results wrapper
        '[class*="searchResults"]',              # Any search results class
        '[class*="product-listing"]',            # Product listing container
        'main[role="main"]',                     # Main content area
        '#main-content',                         # Main content ID
        'main',                                  # Main element fallback
        '#listItems',                            # WARNING: often includes promo carousels; keep as last resort
    ]

    # First, try to find the main grid container to scope our search
    main_container = None
    for container_sel in main_grid_containers:
        try:
            container = page.locator(container_sel).first
            if await container.count() > 0:
                main_container = container
                Actor.log.info(f"Found main grid container: {container_sel}")
                break
        except Exception:
            continue

    # Define card selectors - these should be SPECIFIC to actual product cards
    card_selectors = [
        'div.tile_group',  # Lowe's actual product tile with content
        '[class*="tile_group"]',  # Alternative class selector
        '[data-selector="splp-prd-crd"]',  # Wrapper (may be empty)
        '[class*="product-card"]',
        '[class*="ProductCard"]',
        "[data-test='product-pod']",
        "[data-test='productPod']",
        "div[data-itemid]",
        "li[data-itemid]",
        "[data-itemid]",
    ]

    product_cards = []
    try:
        # If we found the main container, search ONLY within it
        search_base = main_container if main_container else page

        for sel in card_selectors:
            try:
                if main_container:
                    # Scope the search to the main container
                    cards = await asyncio.wait_for(
                        main_container.locator(sel).all(), timeout=15.0
                    )
                else:
                    cards = await asyncio.wait_for(
                        page.locator(sel).all(), timeout=15.0
                    )
                if len(cards) > len(product_cards):
                    product_cards = cards
            except asyncio.TimeoutError:
                continue

    except asyncio.TimeoutError:
        Actor.log.error(f"Timeout finding product cards on page {page_num}")
        raise

    if not product_cards:
        Actor.log.warning(f"No product cards found on page {page_num}")
        return []

    # Extract products with timeout per card
    for card_idx, card in enumerate(product_cards):
        try:
            # If a tile_group contains multiple products, split by data-tile.
            try:
                if await card.locator("[data-tile]").count() > 0 and await card.locator("[data-selector='splp-prd-act-$']").count() > 1:
                    tile_products = await extract_tile_group_products(card)
                    if tile_products:
                        now = datetime.utcnow().isoformat()
                        for p in tile_products:
                            if not p.get("title") or not p.get("url"):
                                continue
                            products.append(
                                {
                                    "title": p.get("title"),
                                    "price": p.get("price", "N/A"),
                                    "was_price": p.get("was_price", ""),
                                    "image_url": p.get("image_url"),
                                    "has_markdown": bool(p.get("was_price")),
                                    "url": p.get("url"),
                                    "category_url": url,
                                    "store_id": store_info["store_id"],
                                    "store_name": store_info["name"],
                                    "store_city": store_info["city"],
                                    "store_state": store_info["state"],
                                    "scraped_at": now,
                                }
                            )
                        continue
            except Exception:
                pass

            # Wrap entire card extraction in timeout
            async def extract_card():
                link_el = card.locator(
                    ":scope a[data-testid='item-description-link'], :scope a[href*='/pd/'], :scope a[data-test*='product-link']"
                ).first
                if await link_el.count() == 0:
                    return None

                href = await link_el.get_attribute("href") or ""
                if not href:
                    return None

                # Title - Lowe's uses data-selector="splp-prd-ttl" for product titles
                title_el = card.locator(
                    ":scope [data-selector='splp-prd-ttl'], :scope [data-testid='item-description'], :scope a[data-testid='item-description-link'], :scope [data-test*='product-title'], :scope h3, :scope h2"
                ).first
                title_text = ""
                if await title_el.count() > 0:
                    title_text = (await title_el.inner_text()).strip()
                if not title_text:
                    # On some /pl/ pages, the /pd/ link wraps the entire card
                    # (including prices + ratings). Avoid using link text as the title.
                    try:
                        aria = (await link_el.get_attribute("aria-label")) or ""
                        title_text = aria.strip()
                    except Exception:
                        title_text = ""

                if (not title_text) or ("$" in title_text) or ("%" in title_text) or ("save" in title_text.lower()):
                    # Best-effort fallback: use the first non-price line from the card blob.
                    try:
                        blob_title = await card.inner_text()
                        for line in (blob_title or "").splitlines():
                            s = (line or "").strip()
                            if not s:
                                continue
                            low = s.lower()
                            if "$" in s:
                                continue
                            if "add to cart" in low or "pickup" in low or "delivery" in low:
                                continue
                            if "save" in low or "savings" in low or "off" == low:
                                continue
                            # Skip bare rating count / noise (e.g. "61")
                            if re.fullmatch(r"[0-9]{1,4}", s):
                                continue
                            title_text = s
                            break
                    except Exception:
                        pass

                prices = await extract_prices_from_card(card)
                price_text = prices.get("price", "N/A")
                was_price = prices.get("was_price", "")

                image_url = None
                try:
                    # Find the actual product image, NOT badge/clearance SVGs
                    all_imgs = await card.locator(":scope img").all()
                    for img in all_imgs:
                        src = (
                            await img.get_attribute("src")
                            or await img.get_attribute("data-src")
                            or await img.get_attribute("data-lazy-src")
                            or ""
                        )
                        if not src:
                            srcset = (
                                await img.get_attribute("srcset")
                                or await img.get_attribute("data-srcset")
                                or ""
                            )
                            first = srcset.split(",")[0].strip()
                            src = first.split(" ")[0].strip() if first else ""
                        
                        # Skip badge/clearance SVGs
                        if "/badges/" in src or src.endswith(".svg"):
                            continue
                        # Skip data: URIs
                        if src.startswith("data:"):
                            continue
                        
                        if src.startswith("//"):
                            src = "https:" + src
                        if src.startswith("/"):
                            src = "https://www.lowes.com" + src
                        
                        # Prefer product images from mobileimages.lowes.com/productimages/
                        if "productimages/" in src or "mobileimages.lowes.com" in src:
                            image_url = src
                            break  # Found the best match
                        
                        # Fallback: any non-badge image with jpg/png extension
                        if not image_url and (".jpg" in src.lower() or ".png" in src.lower() or ".jpeg" in src.lower()):
                            image_url = src
                except Exception:
                    image_url = None

                if title_text and href and len(title_text) > 5:
                    # Filter out bad titles
                    bad_titles = ["pickup today", "free pickup", "delivery", "add to cart", "view details", "unavailable", "out of stock"]
                    if any(bt in title_text.lower() for bt in bad_titles):
                        # Try to fall back to image alt text if available, or just skip
                        alt_title = await card.locator("img").get_attribute("alt")
                        if alt_title and len(alt_title) > 5 and not any(bt in alt_title.lower() for bt in bad_titles):
                            title_text = alt_title
                        else:
                            # Skip this item if we can't find a real title
                            return None

                    return {
                        "title": title_text.strip(),
                        "price": price_text.strip() if price_text else "N/A",
                        "was_price": was_price.strip() if was_price else "",
                        "image_url": image_url,
                        "has_markdown": bool(was_price),
                        "url": f"https://www.lowes.com{href}" if href.startswith("/") else href,
                        "category_url": url,
                        "store_id": store_info["store_id"],
                        "store_name": store_info["name"],
                        "store_city": store_info["city"],
                        "store_state": store_info["state"],
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                return None

            product = await asyncio.wait_for(extract_card(), timeout=5.0)
            if product:
                products.append(product)

        except asyncio.TimeoutError:
            Actor.log.warning(f"Timeout extracting card {card_idx} on page {page_num}")
            continue  # Skip this card
        except Exception as e:
            # Log unexpected errors but continue
            if card_idx == 0:  # Only log first card error to avoid spam
                Actor.log.warning(f"Error extracting card on page {page_num}: {e}")
            continue

    return products


async def scrape_category_all_pages(page: Page, category_url: str, store_info: dict) -> list[dict]:
    """Scrape ALL pages of a category until no more products found"""     
    all_products = []
    cat_name = category_url.split('/pl/')[-1].split('/')[0][:30]

    # 1. Go to page 1 to set "Pickup Today" filter
    try:
        await page.goto(category_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(2)
        try:
            _navlog(
                "category_goto",
                {
                    "store_id": store_info.get("store_id"),
                    "store_name": store_info.get("name"),
                    "cat_name": cat_name,
                    "requested_url": category_url,
                    "landed_url": page.url,
                },
            )
        except Exception:
            pass

        # If Lowe's redirected us to a /c/ category page, abort early.
        if _is_redirected_to_c(page.url):
            _navlog(
                "redirect_to_c",
                {
                    "store_id": store_info.get("store_id"),
                    "store_name": store_info.get("name"),
                    "cat_name": cat_name,
                    "requested_url": category_url,
                    "landed_url": page.url,
                },
            )
            raise RuntimeError(f"Category redirected from /pl/ to /c/ page: {page.url}")

        # Some categories legitimately have zero products (seasonal/legal/empty).
        # In that case, the pickup filter UI will not exist, and we should NOT retry forever.
        try:
            # Match variations: "0 Products.", "could not find any products", "0 results"
            empty_selectors = [
                 'text=/0 Products/i',
                 'text=/0 results/i',
                 'text=/could not find any products/i',
                 'text=/Please reduce your filters/i'
            ]
            for selector in empty_selectors:
                if await page.locator(selector).first.is_visible(timeout=1000):
                    Actor.log.info(f"{store_info['name']} - {cat_name}: Empty results page detected ({selector}); skipping category")
                    return []
        except Exception:
            pass

        # If we're already blocked on the first navigation, abort quickly.
        try:
            title = await asyncio.wait_for(page.title(), timeout=10.0)
            if "Access Denied" in title or "Robot" in title or "Blocked" in title:
                Actor.log.error(f"BLOCKED during setup: {title}")
                raise Exception(f"Blocked by anti-bot: {title}")
        except asyncio.TimeoutError:
            # If title can't be read, let the normal flow attempt filter/page parsing (may error).
            pass

        # Apply human behavior before filter
        await human_mouse_move(page)
        await asyncio.sleep(0.5 + random.random() * 0.5)

        # Apply the robust pickup filter with verification
        filter_applied = await apply_pickup_filter(page, f"{store_info['name']}-{cat_name}")

        if not filter_applied:
            Actor.log.error(f"{store_info['name']} - {cat_name}: Pickup filter DISABLED or could not be applied - SKIPPING CATEGORY ENTIRELY")
            Actor.log.error(f"This means no pickup items are available in this category at {store_info['name']}")
            return []  # Skip this category entirely instead of scraping wrong data

        # CRITICAL: Verify the URL actually has pickup filter parameters
        current_url_lower = page.url.lower()
        has_filter_params = (
            "instock=1" in current_url_lower or
            "pickup" in current_url_lower or
            "refinement" in current_url_lower
        )

        if not has_filter_params:
            Actor.log.error(f"{store_info['name']} - {cat_name}: URL missing pickup filter params after filter was 'applied' - SKIPPING CATEGORY")
            Actor.log.error(f"URL: {page.url}")
            return []  # Don't scrape unfiltered results

        # Update category_url to include the new query params (facets)
        new_url = page.url
        
        # CRITICAL BUG FIX: Validate we're still on a /pl/ product listing page
        # If Lowe's redirected us to a /c/ category page, we CANNOT scrape it (no products)
        # This was causing infinite loops where the scraper kept reloading /c/Generators-Electrical
        if '/c/' in new_url and '/pl/' not in new_url:
            _navlog(
                "redirect_to_c",
                {
                    "store_id": store_info.get("store_id"),
                    "store_name": store_info.get("name"),
                    "cat_name": cat_name,
                    "requested_url": category_url,
                    "landed_url": new_url,
                },
            )
            Actor.log.error(f"{store_info['name']} - {cat_name}: ABORT - Page redirected to /c/ category page: {new_url}")
            Actor.log.error(f"Original /pl/ URL was: {category_url}")
            raise RuntimeError(f"Category redirected from /pl/ to /c/ page - this category has no product listings to scrape")
        
        # Only update URL if we're still on a valid /pl/ product listing page
        if '/pl/' in new_url:
            category_url = new_url
            Actor.log.info(f"{store_info['name']} - {cat_name}: Pickup filter applied, URL now: {category_url[:100]}...")
            _navlog(
                "pickup_applied",
                {
                    "store_id": store_info.get("store_id"),
                    "store_name": store_info.get("name"),
                    "cat_name": cat_name,
                    "category_url": category_url,
                },
            )
        else:
            # Unexpected URL format - keep original and log warning
            Actor.log.warning(f"{store_info['name']} - {cat_name}: URL changed to unexpected format, keeping original: {new_url[:100]}")

    except Exception as e:
        Actor.log.warning(f"{store_info['name']} - Failed setup: {e}")
        raise  # Re-raise to trigger worker retry

    page_num = 1
    consecutive_empty = 0  # Track empty pages to avoid infinite loop
    last_url = None
    same_url_count = 0
    MAX_EMPTY_RETRIES = 3
    MAX_SAME_URL = 3
    
    while True:  # Scrape until we run out of products
        try:
            # Check if we're stuck on the same URL (infinite reload bug)
            current_url = page.url
            if current_url == last_url:
                same_url_count += 1
                if same_url_count >= MAX_SAME_URL:
                    Actor.log.warning(f"{store_info['name']} - {cat_name}: Stuck on same URL {same_url_count} times, moving on")
                    break
            else:
                same_url_count = 0
                last_url = current_url
            
            # Add per-page timeout to prevent infinite hangs
            products = await asyncio.wait_for(
                scrape_category_page(page, category_url, store_info, page_num),
                timeout=120.0  # 2 minutes max per page
            )

            if not products:
                consecutive_empty += 1
                if consecutive_empty >= MAX_EMPTY_RETRIES:
                    Actor.log.info(f"{store_info['name']} - {cat_name}: {consecutive_empty} consecutive empty pages, category done")
                    break
                # Try once more in case of transient issue
                Actor.log.info(f"{store_info['name']} - {cat_name} p{page_num}: Empty ({consecutive_empty}/{MAX_EMPTY_RETRIES}), retrying...")
                await asyncio.sleep(1 + random.random())
                continue
            
            # Reset empty counter on success
            consecutive_empty = 0

            all_products.extend(products)
            Actor.log.info(f"{store_info['name']} - {cat_name} p{page_num}: {len(products)} products")

            # Stop if partial page (end of results)
            if len(products) < 12:
                break

            page_num += 1

        except asyncio.TimeoutError:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: TIMEOUT after 120s")
            break
        except Exception as e:
            Actor.log.error(f"{store_info['name']} - {cat_name} p{page_num}: Error - {e}")
            break

    if all_products:
        Actor.log.info(f"{store_info['name']} - {cat_name}: {len(all_products)} total from {page_num} pages")

    return all_products


# ============================================================================
# MAIN
# ============================================================================

async def main():
    async with Actor:
        # Input
        actor_input = await Actor.get_input() or {}
        test_mode = actor_input.get("testMode", False)
        max_stores = actor_input.get("maxStores", 1 if test_mode else 999)
        max_categories = actor_input.get("maxCategories", 2 if test_mode else 999)
        proxy_url = actor_input.get("proxyUrl")  # External proxy
        state_filter = actor_input.get("stateFilter", ["WA", "OR"])

        Actor.log.info("=" * 70)
        Actor.log.info("Lowe's Full Catalog Scraper")
        Actor.log.info("=" * 70)
        Actor.log.info(f"Test mode: {test_mode}")
        Actor.log.info(f"Max stores: {max_stores}")
        Actor.log.info(f"Max categories: {max_categories}")
        if proxy_url:
            Actor.log.info(f"Proxy: {proxy_url}")

        # Load data
        all_stores, all_categories = load_stores_and_categories()

        # Filter by state
        if state_filter:
            all_stores = [s for s in all_stores if s["state"] in state_filter]

        stores = all_stores[:max_stores]
        categories = all_categories[:max_categories]

        Actor.log.info(f"Scraping {len(stores)} stores x {len(categories)} categories")

        # Scrape each store sequentially (parallel causes blocking)
        total_products = 0

        async with async_playwright() as p:
            for store in stores:
                Actor.log.info(f"\n{'='*70}")
                Actor.log.info(f"Starting store: {store['name']}")
                Actor.log.info(f"{'='*70}")

                # Browser setup
                profile_dir = Path(f".playwright-profiles/store-{store['store_id']}")
                profile_dir.mkdir(parents=True, exist_ok=True)

                launch_kwargs = {
                    "headless": False,  # Must be False - Lowe's blocks headless
                    "channel": "chrome",
                    "viewport": {"width": 1440, "height": 900},
                    "locale": "en-US",
                    "timezone_id": "America/Los_Angeles",
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--disable-infobars",
                        "--disable-gpu",  # Reduce GPU process overhead
                        "--no-sandbox",  # Reduce process spawning
                        "--disable-background-networking",  # Prevent background resource usage
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--memory-pressure-off",  # Prevent memory-based crashes
                    ]
                }

                if proxy_url:
                    launch_kwargs["proxy"] = {"server": proxy_url}

                context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
                page = context.pages[0] if context.pages else await context.new_page()

                try:
                    # Setup
                    await warmup_session(page)
                    await set_store_context(page, store["url"], store["name"])

                    # Scrape categories
                    store_products = []
                    for idx, category_url in enumerate(categories):
                        try:
                            products = await scrape_category_all_pages(page, category_url, store)
                            store_products.extend(products)

                            # Push incrementally
                            if products:
                                await Actor.push_data(products)

                            await asyncio.sleep(2.0 + random.random() * 2.55)  # 2.0-4.55 sec (30% inc) between categories

                        except Exception as e:
                            # Log the error but continue with next category
                            Actor.log.error(f"Error scraping category {idx}: {e}")
                            # If it's a timeout or browser crash, this category failed - move on
                            continue

                    total_products += len(store_products)
                    Actor.log.info(f"Store complete: {len(store_products)} products from {store['name']}")

                except Exception as e:
                    Actor.log.error(f"Error scraping {store['name']}: {e}")
                finally:
                    await context.close()

        Actor.log.info("=" * 70)
        Actor.log.info(f"ALL DONE! Total products: {total_products}")
        Actor.log.info("=" * 70)
