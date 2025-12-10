"""Parallel Lowe's scraper that fans out per store with mobile Playwright contexts."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from app.logging_config import get_logger
import app.selectors as selectors
from app.playwright_env import apply_stealth, headless_enabled, launch_kwargs, mouse_jitter_enabled, category_delay_bounds
from app.extractors.dom_utils import human_wait
from app.retailers.lowes import scrape_category

LOGGER = get_logger(__name__)

# Conservative defaults; override via CLI flags for more aggressive crawling
DEFAULT_NAV_CONCURRENCY = 2
DEFAULT_STORE_LIMIT = 10
DEFAULT_MAX_DEPARTMENTS: int | None = None  # None means all
DEFAULT_DEVICE = "Pixel 5"
DEFAULT_HUMAN_WAIT = (3.0, 7.0)  # seconds between navigations per store
BACK_AISLE_PAGE_SIZE = 24
CLEARANCE_THRESHOLD = 0.25
URL_BLOCKLIST = (
    "/c/accessible-home",
    "/c/accessible-bathroom",
    "/c/accessible-kitchen",
    "/pl/save-now",
    "save-now",
    "savenow",
    "black-friday",
    "blackfriday",
    "/bf/",
    "cyber-monday",
    "/deals",
    "/savings",
    "/special",
    "/clearance",
    "/c/deals",
    "/c/savings",
    "/pl/deals",
    "/pl/savings",
    "promotion",
    "promo",
    "weekly-ad",
    "gift",
    "/departments",
    "/ideas",
    "/inspiration",
    "/how-to",
    "/projects",
    "/l/",
    "/b/",
    "lowesbrands",
)
PRODUCT_SELECTORS = [
    "[data-automation='product-card']",
    "[data-automation*='product-card']",
    "[data-testid='product-card']",
    "[data-testid*='product-card']",
    "[data-test-id='product-card']",
    "[data-test-id*='product-card']",
    "article[data-test-id*='product']",
    "article[data-testid*='product']",
    "div[data-test-id*='plp-grid'] article",
    "div[data-testid*='plp-grid'] article",
    "[data-type='plp-product']",
    ".product-tile",
    "li.grid-tile",
]


def _audit(message: str, *, store_id: str | None = None, dept: str | None = None, url: str | None = None, **extra) -> None:
    payload = {k: v for k, v in {"store": store_id, "dept": dept, "url": url, **extra}.items() if v}
    if payload:
        LOGGER.info(message, extra=payload)
    else:
        LOGGER.info(message)


@dataclass(frozen=True)
class Store:
    id: str
    url: str


def _dedupe_preserve_order(urls: Iterable[str]) -> list[str]:
    seen = OrderedDict()
    for u in urls:
        seen[u] = None
    return list(seen.keys())


def parse_lowes_map(path: Path) -> tuple[list[Store], list[str]]:
    """
    Parse LowesMap.txt for:
      - ALL Washington AND Oregon stores
      - Department/category URLs
    The file is a markdown-ish report; we extract all WA/OR store URLs.
    """
    text = path.read_text(encoding="utf-8")

    # Extract ALL WA and OR store URLs from the entire file
    store_matches = list(
        re.finditer(
            r"https?://www\.lowes\.com/store/(WA-|OR-)([^/]+)/(?P<id>\d{4})",
            text,
            re.IGNORECASE,
        )
    )
    stores: list[Store] = []
    seen_store_ids = set()
    for m in store_matches:
        store_id = m.group("id")
        # Deduplicate by store_id (some stores appear multiple times in the file)
        if store_id in seen_store_ids:
            continue
        seen_store_ids.add(store_id)
        url = m.group(0)  # Full URL including store ID
        stores.append(Store(id=store_id, url=url))

    # Find department section
    lower = text.lower()
    dept_anchor = lower.find("## all department/category urls")
    if dept_anchor == -1:
        raise RuntimeError("Could not find '## ALL DEPARTMENT/CATEGORY URLs' section in LowesMap.txt")
    dept_section = text[dept_anchor:]
    dept_urls = [
        match.group(0).rstrip(")>.,;")  # trim trailing punctuation from markdown bullets
        for match in re.finditer(r"https?://www\.lowes\.com/[^\s\)]+", dept_section, re.IGNORECASE)
    ]

    if not stores:
        raise RuntimeError("No WA/OR store URLs found in LowesMap.txt")
    if not dept_urls:
        raise RuntimeError("No department/category URLs found in LowesMap.txt")

    return stores, _dedupe_preserve_order(dept_urls)


def filter_departments(urls: Sequence[str], max_count: int | None) -> list[str]:
    """
    Drop obvious non-product landing pages and truncate if requested.
    Heuristics: skip the global landing pages that consistently time out or have no grid, and
    prioritize product list ("/pl/") URLs first.

    IMPORTANT: This aggressively filters out deals, savings, Black Friday, and other promotional
    pages to focus on regular department inventory only.
    """
    filtered: list[str] = []
    pl_urls: list[str] = []
    other_urls: list[str] = []
    for url in urls:
        lower = url.lower()

        # Apply blocklist - skip any URL containing blocked terms
        if any(bad in lower for bad in URL_BLOCKLIST):
            LOGGER.debug("Filtered out blocked URL: %s", url)
            continue

        # Categorize remaining URLs
        if "/pl/" in lower:
            pl_urls.append(url)
        elif "/c/" in lower:
            # Only include /c/ URLs if they look like department pages, not deals/savings
            other_urls.append(url)
        else:
            # Skip URLs that don't match expected department patterns
            LOGGER.debug("Filtered out non-department URL: %s", url)
            continue

    # Prioritize /pl/ URLs as they're more likely to have product grids
    filtered.extend(pl_urls)
    filtered.extend(other_urls)

    if max_count is not None:
        return filtered[:max_count]
    return filtered


async def wait_for_products(page) -> str:
    selector_candidates: list[str] = []
    primary = getattr(selectors, "CARD", "") or ""
    alt = getattr(selectors, "CARD_ALT", "") or ""
    if primary:
        selector_candidates.append(primary)
    if alt:
        selector_candidates.append(alt)
    selector_candidates.extend(PRODUCT_SELECTORS)

    for selector in selector_candidates:
        try:
            await page.wait_for_selector(selector, timeout=12_000, state="visible")
            return selector
        except PlaywrightTimeoutError:
            continue
    raise PlaywrightTimeoutError("No product grid located")


async def human_pause(bounds: tuple[float, float]) -> None:
    lo, hi = bounds
    if hi <= 0:
        return
    await asyncio.sleep(random.uniform(lo, hi))


async def _jitter_mouse(page) -> None:
    """Randomise cursor movement to mimic human browsing."""

    if not mouse_jitter_enabled():
        return

    try:
        width = await page.evaluate("() => window.innerWidth || 1280")
        height = await page.evaluate("() => window.innerHeight || 800")
    except Exception:
        width, height = 1280, 800

    try:
        for _ in range(random.randint(1, 3)):
            target_x = random.randint(0, int(max(width, 1)))
            target_y = random.randint(0, int(max(height, 1)))
            steps = random.randint(3, 7)
            await page.mouse.move(target_x, target_y, steps=steps)
            await human_wait(120, 320, obey_policy=False)
    except Exception:
        # Non-fatal; simply skip cursor jitter if Playwright rejects the move.
        return


async def scrape_products(page, selector: str) -> list[dict[str, str | None]]:
    # Insert richer extraction here if you want SKU, URLs, inventory, etc.
    cards = await page.query_selector_all(selector)
    out: list[dict[str, str | None]] = []
    for card in cards:
        title_el = await card.query_selector(
            "[data-automation='product-title'],"
            "[data-testid*='product-title'],"
            "[data-test-id*='product-title'],"
            "a[data-test-id*='product-title'],"
            "a[data-testid*='product-title'],"
            "a h2, h2, h3"
        )
        price_el = await card.query_selector(
            "[data-automation='product-price'],"
            "[data-testid*='price'],"
            "[data-test-id*='price'],"
            "[data-test-price],"
            "[aria-label*='$'],"
            "span[class*='price'],"
            ".a-price"
        )
        title = (await title_el.inner_text()) if title_el else None
        price = (await price_el.inner_text()) if price_el else None
        if title:
            out.append({"name": title.strip(), "price": price.strip() if price else None})
    return out


async def apply_pickup_filter(page) -> None:
    """Attempt to click the 'Pickup Today' / local availability filter on PLP."""

    selectors = [
        "input[type='checkbox'][aria-label*='Pickup Today']",
        "label[for*='pickup'][aria-label*='Pickup']",
        "text=Pickup Today",
        "span:has-text('Pickup Today')",
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_timeout(1200)
                _audit("Applied pickup filter", url=page.url)
                return
        except Exception:
            continue


async def paginate_products(
    page,
    selector: str,
    max_pages: int | None = 50,
    *,
    category_name: str,
    store_id: str | None,
) -> list[dict[str, object]]:
    """Scrape current page and keep advancing via on-page Next controls."""

    all_products: list[dict[str, object]] = []
    page_idx = 0
    page_size = 24
    while True:
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1200)
        except Exception:
            pass
        try:
            await wait_for_products(page)
        except PlaywrightTimeoutError:
            break

        # We expect scrape_category to handle deeper extraction; here only collect minimal to advance pages.
        products = await scrape_products(page, selector)
        all_products.extend(products)
        page_idx += 1
        if max_pages is not None and page_idx >= max_pages:
            break

        candidates = []
        selector_variants = []
        next_selector = getattr(selectors, "NEXT_BTN", "") or ""
        if next_selector:
            selector_variants.append(next_selector)
        selector_variants.append(
            "[data-testid*='pagination-next'], a[rel='next'], "
            "button[aria-label*='Next'], a[aria-label*='Next'], "
            "button[title*='Next'], a[title*='Next'], "
            "button[aria-label*='next page'], a[aria-label*='next page'], "
            "button:has-text('>'), a:has-text('>')"
        )
        for sel in selector_variants:
            try:
                candidates = await page.query_selector_all(sel)
                if candidates:
                    break
            except Exception:
                continue
        next_btn = None
        for candidate in candidates:
            try:
                disabled = await candidate.get_attribute("disabled")
                aria_disabled = await candidate.get_attribute("aria-disabled")
                if (disabled and disabled.strip().lower() in ("true", "disabled")) or (
                    aria_disabled and aria_disabled.strip().lower() in ("true", "disabled")
                ):
                    continue
                next_btn = candidate
                break
            except Exception:
                continue
        if not next_btn:
            break

        try:
            current_url = page.url
            await next_btn.click()
            await page.wait_for_timeout(1500)
            _audit("Clicked paginated Next", url=current_url)
            try:
                await page.wait_for_function("url => location.href !== url", arg=current_url, timeout=7000)
            except Exception:
                pass
            if page.url == current_url:
                break
            # Heuristic: if the next page still shows fewer than a full page of products, stop.
            try:
                await wait_for_products(page)
                next_products = await scrape_products(page, selector)
                if len(next_products) < max(4, page_size // 3):
                    all_products.extend(next_products)
                    break
                all_products.extend(next_products)
                page_idx += 1
                if max_pages is not None and page_idx >= max_pages:
                    break
                continue
            except Exception:
                break
        except Exception:
            break

    return all_products


def _prepare_pagination_url(url: str, store_id: str | None, *, offset: int = 0) -> str:
    """
    Mirror the launch.bat (app.main) behaviour: persist store context and bias to
    pickup/in-stock plus offset pagination.
    """
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.setdefault("pickupType", "pickupToday")
    params.setdefault("availability", "pickupToday")
    params["inStock"] = "1"
    params.setdefault("rollUpVariants", "0")
    if store_id and store_id.strip():
        params.setdefault("storeNumber", store_id.strip())
    params["offset"] = str(max(offset, 0))
    rebuilt = parsed._replace(query=urlencode(params, doseq=True))
    return rebuilt.geturl()


async def paginate_by_offset(
    page,
    base_url: str,
    page_size: int,
    selector: str,
    *,
    category_name: str,
    store_id: str | None = None,
    max_pages: int | None = None,
) -> list[dict[str, object]]:
    """Offset-based pagination: ?offset=24*(n-1) using the same product selector."""

    parsed = urlparse(base_url)
    base_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    results: list[dict[str, object]] = []

    # Start from page 2 (offset page_size), since caller already scraped page 1.
    for idx in range(1, max_pages or 50):
        offset_val = page_size * idx
        query = base_query.copy()
        query["offset"] = str(offset_val)
        target_url = _prepare_pagination_url(base_url, store_id, offset=offset_val)
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=40_000)
            await page.wait_for_load_state("networkidle", timeout=10_000)
            await _jitter_mouse(page)
            await wait_for_products(page)
        except PlaywrightTimeoutError:
            break
        products = await scrape_products(page, selector)
        _audit(
            "Offset pagination page scraped",
            url=target_url,
            dept=base_url,
            extra_count=len(products),
        )
        if not products:
            break
        results.extend(products)
        if len(products) < page_size:
            break
    return results


async def _extract_child_links(page, max_children: int = 10) -> list[str]:
    """Collect candidate subcategory links from a landing page."""

    links = await page.query_selector_all("a[href]")
    child_urls: list[str] = []
    for link in links:
        href = await link.get_attribute("href")
        if not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("/"):
            href = "https://www.lowes.com" + href
        lower = href.lower()
        if "lowes.com" not in lower:
            continue
        # Skip obvious brand/promo pages.
        if "/b/" in lower or "brand" in lower:
            continue
        if any(bad in lower for bad in URL_BLOCKLIST):
            continue
        if "/pl/" not in lower and "/c/" not in lower:
            continue
        if href in child_urls:
            continue
        child_urls.append(href)
        if len(child_urls) >= max_children:
            break
    return child_urls


async def crawl_department(
    page,
    dept_url: str,
    *,
    store_id: str | None = None,
) -> list[dict[str, object]]:
    """Use the launch.bat extraction (scrape_category) for a single department URL."""

    results: list[dict[str, object]] = []
    try:
        target_url = _prepare_pagination_url(dept_url, store_id, offset=0)
        await page.goto(target_url, wait_until="domcontentloaded", timeout=40_000)
        await page.wait_for_load_state("networkidle", timeout=10_000)
        _audit("Visiting department", url=target_url, dept=dept_url)
        await _jitter_mouse(page)

        rows = await scrape_category(
            page,
            target_url,
            dept_url,
            store_id or "",
            store_id,
            clearance_threshold=CLEARANCE_THRESHOLD,
        )
        if rows:
            results.append({"department": dept_url, "products": rows})
            _audit("Captured product grid", url=dept_url, dept=dept_url, extra_count=len(rows))
        else:
            _audit("No products extracted", url=dept_url, dept=dept_url)
    except PlaywrightTimeoutError:
        _audit("Timeout on department", url=dept_url, dept=dept_url)
    except Exception as exc:
        LOGGER.warning("Error on %s: %s", dept_url, exc)

    return results


async def discover_and_scrape(
    page, dept_url: str, store_id: str | None
) -> tuple[list[dict[str, object]], bool]:
    """
    Attempt to scrape the provided department URL. If no product grid is found, try to
    drill into subcategory links ("/pl/" first) up to a small cap.
    Returns (results, success_flag).
    """
    try:
        crawled = await crawl_department(page, dept_url, max_depth=0, max_children=0, store_id=store_id)
        return crawled, bool(crawled)
    except PlaywrightTimeoutError:
        return [], False


async def drill_subcategories(page, parent_url: str, max_children: int = 5) -> list[dict[str, object]]:
    """
    When a department landing page has no grid, try a handful of subcategory links that
    look like product lists.
    """
    results: list[dict[str, object]] = []
    links = await page.query_selector_all("a[href]")
    child_urls: list[str] = []
    for link in links:
        href = await link.get_attribute("href")
        if not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        if href.startswith("/"):
            href = "https://www.lowes.com" + href
        lower = href.lower()
        if "lowes.com" not in lower:
            continue
        if "/pl/" not in lower and "/c/" not in lower:
            continue
        if any(bad in lower for bad in URL_BLOCKLIST):
            continue
        if "save-now" in lower:
            continue
        if href in child_urls:
            continue
        child_urls.append(href)
        if len(child_urls) >= max_children:
            break

    for child in child_urls:
        try:
            await page.goto(child, wait_until="domcontentloaded", timeout=30_000)
            await _jitter_mouse(page)
            selector = await wait_for_products(page)
            seen_keys: set[tuple[str | None, str | None]] = set()
            products = await paginate_products(
                page,
                selector,
                max_pages=2,
                category_name=child,
                store_id=None,
                seen_keys=seen_keys,
                clearance_threshold=CLEARANCE_THRESHOLD,
            )
            results.append({"department": child, "products": products})
            _audit("Drilled subcategory", url=child, dept=parent_url, extra_count=len(products))
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue
    return results


async def run_store_worker(
    browser,
    device,
    store: Store,
    departments: Sequence[str],
    nav_sem: asyncio.Semaphore,
    human_wait_bounds: tuple[float, float],
) -> None:
    context = await browser.new_context(**device, locale="en-US")
    page = await context.new_page()

    # CRITICAL FIX: Extract ZIP code from store page, then use proper set_store_context
    zip_code = None
    store_name = None

    try:
        async with nav_sem:
            _audit("Extracting ZIP from store page", store_id=store.id, url=store.url)
            await page.goto(store.url, wait_until="domcontentloaded", timeout=40_000)
            await page.wait_for_load_state("networkidle", timeout=15_000)
            await human_wait(800, 1500, obey_policy=False)

            # Extract ZIP code from the store page
            # Try multiple methods to find the ZIP
            try:
                # Method 1: Look for ZIP in page text using regex
                page_text = await page.content()
                import re
                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', page_text)
                if zip_match:
                    zip_code = zip_match.group(1)
                    _audit("Found ZIP via regex", store_id=store.id, zip=zip_code)

                # Method 2: Try to find address elements
                if not zip_code:
                    address_selectors = [
                        "[itemprop='postalCode']",
                        "[class*='zip']",
                        "[class*='postal']",
                        "address",
                    ]
                    for sel in address_selectors:
                        try:
                            elem = await page.query_selector(sel)
                            if elem:
                                text = await elem.inner_text()
                                zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', text)
                                if zip_match:
                                    zip_code = zip_match.group(1)
                                    _audit("Found ZIP in address element", store_id=store.id, zip=zip_code, selector=sel)
                                    break
                        except Exception:
                            continue

                # Method 3: Try store name element for store name
                store_name_selectors = [
                    "h1",
                    "[class*='store-name']",
                    "[class*='storeName']",
                ]
                for sel in store_name_selectors:
                    try:
                        elem = await page.query_selector(sel)
                        if elem:
                            name_text = await elem.inner_text()
                            if name_text and "lowe" in name_text.lower():
                                store_name = name_text.strip()
                                _audit("Found store name", store_id=store.id, name=store_name)
                                break
                    except Exception:
                        continue

            except Exception as exc:
                LOGGER.warning("[%s] Failed to extract ZIP from store page: %s", store.id, exc)

            # If we still don't have a ZIP, use store ID as fallback (some store IDs are ZIPs)
            if not zip_code:
                # Try using store ID as ZIP if it's 5 digits
                if len(store.id) == 5 and store.id.isdigit():
                    zip_code = store.id
                    _audit("Using store ID as ZIP fallback", store_id=store.id, zip=zip_code)
                else:
                    # Last resort: use a default WA ZIP and rely on store_id hint
                    zip_code = "98101"  # Seattle ZIP as fallback
                    _audit("Using default Seattle ZIP as fallback", store_id=store.id, zip=zip_code)

    except Exception as exc:
        LOGGER.error("[%s] Failed to load store page: %s", store.id, exc)
        zip_code = "98101"  # Fallback to Seattle

    # Now use the PROPER set_store_context from working crawler
    try:
        async with nav_sem:
            _audit("Calling set_store_context", store_id=store.id, zip=zip_code)

            # Build store hint with store_id so it selects the right store
            store_hint = {"store_id": store.id}
            if store_name:
                store_hint["store_name"] = store_name

            selected_store_id, selected_store_name = await set_store_context(
                page=page,
                zip_code=zip_code,
                user_agent=None,
                store_hint=store_hint,
            )

            _audit("Store context set successfully",
                   store_id=selected_store_id,
                   name=selected_store_name,
                   zip=zip_code)

    except Exception as exc:
        LOGGER.error("[%s] Failed to set store context: %s", store.id, exc)
        await context.close()
        return

    results: list[dict[str, object]] = []

    # Process each department using the WORKING scrape_category logic
    for dept_url in departments:
        await human_pause(human_wait_bounds)
        try:
            async with nav_sem:
                # Use the WORKING pagination logic from lowes.py
                dept_name = dept_url.split("/")[-1] if "/" in dept_url else dept_url
                _audit("Starting department", store_id=store.id, dept=dept_name, url=dept_url)

                # Call scrape_category from the working crawler with proper parameters
                products = await scrape_category(
                    page=page,
                    url=dept_url,
                    category_name=dept_name,
                    zip_code=store.id,  # Use store ID as ZIP for logging
                    store_id=store.id,
                    clearance_threshold=0.0,  # Get all items, not just clearance
                )

                if products:
                    results.append({"department": dept_url, "store_id": store.id, "products": products})
                    LOGGER.info("[%s] %s -> %d products", store.id, dept_name, len(products))
                    _audit("Department complete", store_id=store.id, dept=dept_name, url=dept_url, extra_count=len(products))
                else:
                    LOGGER.warning("[%s] No products found on %s", store.id, dept_name)

        except PlaywrightTimeoutError:
            LOGGER.warning("[%s] Timeout on %s", store.id, dept_url)
            continue
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("[%s] Error on %s: %s", store.id, dept_url, exc)
            continue

    out_dir = Path("outputs/stores")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"store_{store.id}_data.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    LOGGER.info("[%s] Wrote %s with %d departments", store.id, out_path, len(results))

    await context.close()


async def orchestrate(
    map_path: Path,
    store_limit: int,
    nav_concurrency: int,
    device_name: str,
    human_wait_bounds: tuple[float, float],
    max_departments: int | None,
) -> None:
    stores, departments = parse_lowes_map(map_path)
    stores = stores[:store_limit]
    departments = filter_departments(departments, max_departments)
    LOGGER.info("Loaded %d Washington stores (top %d requested)", len(stores), store_limit)
    LOGGER.info("Loaded %d department URLs after filtering", len(departments))

    async with async_playwright() as p:
        apply_stealth(p)
        device = p.devices[device_name]
        # Override headless if user set CHEAPSKATER_HEADLESS
        browser = await p.chromium.launch(**{**launch_kwargs(), "headless": headless_enabled()})
        nav_sem = asyncio.Semaphore(max(1, nav_concurrency))

        tasks = [
            run_store_worker(browser, device, store, departments, nav_sem, human_wait_bounds)
            for store in stores
        ]
        await asyncio.gather(*tasks)
        await browser.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Parallel Lowe's store crawler (mobile contexts).")
    parser.add_argument(
        "--map",
        type=Path,
        default=Path("..") / "LowesMap.txt",
        help="Path to LowesMap.txt containing WA stores + departments.",
    )
    parser.add_argument(
        "--store-limit",
        type=int,
        default=DEFAULT_STORE_LIMIT,
        help="Number of WA stores to crawl (top N from the map).",
    )
    parser.add_argument(
        "--nav-cap",
        type=int,
        default=DEFAULT_NAV_CONCURRENCY,
        help="Max in-flight navigations to avoid velocity blocking.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=DEFAULT_DEVICE,
        help='Playwright device descriptor to emulate (e.g., "Pixel 5", "iPhone 12").',
    )
    parser.add_argument(
        "--human-wait",
        type=float,
        nargs=2,
        metavar=("MIN_SEC", "MAX_SEC"),
        default=DEFAULT_HUMAN_WAIT,
        help="Randomized wait between department navigations per store.",
    )
    parser.add_argument(
        "--max-departments",
        type=int,
        default=DEFAULT_MAX_DEPARTMENTS,
        help="Limit number of departments to crawl (after filtering). Omit for all.",
    )
    args = parser.parse_args(argv)

    asyncio.run(
        orchestrate(
            map_path=args.map,
            store_limit=args.store_limit,
            nav_concurrency=args.nav_cap,
            device_name=args.device,
            human_wait_bounds=category_delay_bounds(),
            max_departments=args.max_departments,
        )
    )


if __name__ == "__main__":
    main()
