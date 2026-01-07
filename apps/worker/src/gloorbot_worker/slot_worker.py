from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

# Handle PyInstaller frozen executable - need absolute imports
if getattr(sys, 'frozen', False):
    from gloorbot_worker import api
    from gloorbot_worker.navlog import default_event_logger, set_default_parallel_navlog_path
    from gloorbot_worker.paths import logs_dir, profiles_dir, status_dir
else:
    from . import api
    from .navlog import default_event_logger, set_default_parallel_navlog_path
    from .paths import logs_dir, profiles_dir, status_dir


DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "0.50"))
COOLDOWN_SECONDS = int(os.getenv("BLOCK_COOLDOWN_SECONDS", "300"))
MAX_CATEGORY_SECONDS = int(os.getenv("MAX_CATEGORY_SECONDS", "1200"))

_FALSE_VALUES = {"0", "false", "no", "off"}

_DIAG_FALSE_VALUES = {"0", "false", "no", "off", ""}


def _deal_diag_enabled() -> bool:
    return os.getenv("GLOORBOT_DEAL_DIAGNOSTICS", "").strip().lower() not in _DIAG_FALSE_VALUES


def _deal_diag_path(slot_id: int) -> Path:
    out_dir = logs_dir() / "deal_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"slot_{slot_id}.jsonl"


def _deal_diag_write(slot_id: int, event: dict[str, Any]) -> None:
    if not _deal_diag_enabled():
        return
    try:
        event = dict(event)
        event.setdefault("ts", datetime.utcnow().isoformat())
        event.setdefault("event", "deal_candidate")
        event.setdefault("slot_id", slot_id)
        path = _deal_diag_path(slot_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        return


def _signal_block() -> None:
    """Signal to the supervisor that a block was detected."""
    try:
        block_signal = status_dir() / "block_signal.txt"
        # Write timestamp so supervisor knows it's fresh
        block_signal.write_text(str(time.time()), encoding="utf-8")
    except Exception:
        pass


def _normalize_lowes_url(url: str) -> str:
    if not url:
        return url
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return url
        if parsed.netloc.endswith("lowes.com"):
            return urlunparse(
                (
                    "https",
                    "www.lowes.com",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        return url
    except Exception:
        return url


async def _dump_block_artifacts(*, slot_id: int, lease: api.Lease, page: Any, error: Exception) -> None:
    if os.getenv("GLOORBOT_BLOCK_DIAGNOSTICS", "0").strip().lower() in _FALSE_VALUES:
        return
    try:
        block_dir = logs_dir() / "blocks"
        block_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        prefix = f"slot{slot_id}_task{getattr(lease, 'task_id', 'unknown')}_{ts}"

        meta: dict[str, Any] = {
            "slot_id": slot_id,
            "task_id": getattr(lease, "task_id", None),
            "store_id": getattr(lease, "store_id", None),
            "store_url": getattr(lease, "store_url", None),
            "category_url": getattr(lease, "category_url", None),
            "page_url": getattr(page, "url", None),
            "error": str(error),
        }
        try:
            meta["title"] = await page.title()
        except Exception:
            pass
        try:
            meta["navigator_ua"] = await page.evaluate("() => navigator.userAgent")
            meta["navigator_webdriver"] = await page.evaluate("() => navigator.webdriver")
        except Exception:
            pass
        try:
            import importlib.metadata as _m

            meta["playwright"] = _m.version("playwright")
        except Exception:
            pass

        (block_dir / f"{prefix}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        try:
            await page.screenshot(path=str(block_dir / f"{prefix}.png"), full_page=True)
        except Exception:
            pass
        try:
            html = await page.content()
            (block_dir / f"{prefix}.html").write_text(html, encoding="utf-8")
        except Exception:
            pass
    except Exception:
        # Never crash the worker due to diagnostics
        return


def _find_parallel_dir() -> Path:
    # PyInstaller: data is unpacked into sys._MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve()))
    candidate = base / "PARALLEL"
    if candidate.exists():
        return candidate

    # Dev: walk upward until repo root found
    cur = Path(__file__).resolve()
    for p in [cur] + list(cur.parents):
        cand = p / "PARALLEL"
        if (cand / "scraper.py").exists():
            return cand
    raise FileNotFoundError("Could not locate PARALLEL/ folder")


def _enable_price_diagnostics_for_slot(slot_id: int) -> None:
    """
    Enable maximum-verbosity price diagnostics for the embedded PARALLEL scraper.
    This writes JSONL to a per-slot file so multi-slot runs don't interleave.
    """
    if os.getenv("GLOORBOT_PRICE_DIAGNOSTICS", "0").strip().lower() in _FALSE_VALUES:
        return
    try:
        out_dir = logs_dir() / "price_diagnostics"
        out_dir.mkdir(parents=True, exist_ok=True)
        os.environ["GLOORBOT_PRICE_DIAG_PATH"] = str(out_dir / f"slot_{slot_id}.jsonl")
        # Keep lots of context by default, but allow override.
        os.environ.setdefault("GLOORBOT_PRICE_DIAG_MAXLEN", "1200")
    except Exception:
        return


def _load_parallel_scraper() -> Any:
    import importlib.util

    parallel_dir = _find_parallel_dir()
    scraper_path = parallel_dir / "scraper.py"
    spec = importlib.util.spec_from_file_location("parallel_scraper", str(scraper_path))
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load PARALLEL scraper module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


_PRICE_RE = re.compile(r"\$?\s*([0-9]{1,5})(?:[.,]\s*([0-9]{2}))?")


def _to_float_price(text: str) -> float | None:
    if not text:
        return None
    low = text.lower()
    # Reject financing/monthly payment snippets (these are not the product price).
    # Examples seen on Lowe's: "$125/mo Suggested payments...", "Buy Now, Pay Later ... monthly payments".
    if (
        "/mo" in low
        or "per month" in low
        or "monthly payment" in low
        or "monthly payments" in low
        or "suggested payment" in low
        or "suggested payments" in low
        or "special financing" in low
        or "pay later" in low
        or "buy now" in low
        or "learn how" in low
        or "when you choose" in low
        or "eligible purchases" in low
        or "protection" in low
        or "plan" in low
        or "warranty" in low
        or "accessory" in low
    ):
        return None
    # Normalize weird newlines like "$\n42\n.29"
    compact = re.sub(r"\s+", "", text)
    # Remove thousand separators like "$1,049.90" -> "$1049.90"
    compact = compact.replace(",", "")
    # Avoid interpreting non-price discount labels as money (e.g. "Save 5%").
    if "$" not in compact:
        if "%" in compact:
            return None
        if re.search(r"(?i)\b(save|savings|off)\b", text):
            return None
    # Prefer explicit $ patterns first
    m = re.search(r"\$([0-9]{1,5})(?:\.([0-9]{2}))?", compact)
    if m:
        whole = m.group(1)
        cents = m.group(2) or "00"
        try:
            return float(f"{whole}.{cents}")
        except Exception:
            return None
    # Fallback to loose match
    m2 = _PRICE_RE.search(compact)
    if not m2:
        return None
    whole = m2.group(1)
    cents = m2.group(2) or "00"
    try:
        return float(f"{whole}.{cents}")
    except Exception:
        return None


def _deal_from_product(p: dict, category_url: str) -> dict | None:
    slot_id = int(os.getenv("GLOORBOT_SLOT_ID", "0") or "0")
    if _deal_diag_enabled():
        _deal_diag_write(
            slot_id,
            {
                "stage": "input",
                "category_url": category_url,
                "product_url": p.get("url"),
                "title": (p.get("title") or "")[:200],
                "price_raw": p.get("price"),
                "was_price_raw": p.get("was_price"),
            },
        )
    price_now = _to_float_price(str(p.get("price", "")))
    was_price = _to_float_price(str(p.get("was_price", "")))
    if not price_now or not was_price or was_price <= 0:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "missing_or_invalid_price",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                    "price_raw": p.get("price"),
                    "was_price_raw": p.get("was_price"),
                },
            )
        return None
    # Guard against obvious parse noise (e.g. "$4" captured from unrelated text
    # on a high-ticket item). We prefer dropping a rare true extreme deal over
    # spamming false positives.
    if was_price >= 200 and price_now <= 10:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "high_ticket_tiny_price",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                },
            )
        return None
    # Ensure price is actually discounted (price < was_price)
    if price_now >= was_price:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "not_discounted",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                },
            )
        return None
    pct_off = (was_price - price_now) / was_price
    # Additional sanity: extremely high discounts on expensive items are almost
    # always parse errors. Keep the general >=50% rule but reject the most
    # suspicious tail.
    if was_price >= 200 and pct_off > 0.97:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "suspicious_extreme_pct_off",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                    "pct_off": pct_off,
                },
            )
        return None
    # Reject absurdly high was_prices that are clearly parse errors.
    # No retail appliance, tool, or home item costs $10,000+ at Lowe's.
    if was_price >= 10000:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "absurd_was_price",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                },
            )
        return None
    # Reject deals where the "savings" exceeds $5000 - these are malformed captures.
    if (was_price - price_now) > 5000:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "absurd_savings_delta",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                    "delta": was_price - price_now,
                },
            )
        return None
    if pct_off < DEAL_THRESHOLD:
        if _deal_diag_enabled():
            _deal_diag_write(
                slot_id,
                {
                    "stage": "reject",
                    "reason": "below_threshold",
                    "category_url": category_url,
                    "product_url": p.get("url"),
                    "price_now": price_now,
                    "was_price": was_price,
                    "pct_off": pct_off,
                    "threshold": DEAL_THRESHOLD,
                },
            )
        return None
    image_url = p.get("image_url")
    if isinstance(image_url, str):
        image_url = image_url.strip() or None
        if image_url and not (image_url.startswith("http://") or image_url.startswith("https://")):
            image_url = None
        if image_url:
            image_url = image_url[:2048]
    else:
        image_url = None
    deal = {
        "store_id": p.get("store_id"),
        "store_name": p.get("store_name"),
        "category_url": category_url,
        "product_url": p.get("url"),
        "title": p.get("title", "")[:2048],
        "image_url": image_url,
        "price": float(price_now),
        "was_price": float(was_price),
        "pct_off": float(round(pct_off, 4)),
        "found_at": datetime.utcnow().isoformat(),
    }
    if _deal_diag_enabled():
        _deal_diag_write(
            slot_id,
            {
                "stage": "accept",
                "category_url": category_url,
                "product_url": deal.get("product_url"),
                "price_now": price_now,
                "was_price": was_price,
                "pct_off": deal.get("pct_off"),
                "deal_threshold": DEAL_THRESHOLD,
            },
        )
    return deal


async def _run_slot(client_id: str, slot_id: int) -> None:
    # Ensure navigation logging for PARALLEL is enabled by default (to file), but
    # allow overriding via env vars set by the supervisor/installer.
    try:
        set_default_parallel_navlog_path(slot_id=slot_id)
    except Exception:
        pass

    eventlog = default_event_logger(slot_id=slot_id)
    _enable_price_diagnostics_for_slot(slot_id=slot_id)
    os.environ["GLOORBOT_SLOT_ID"] = str(slot_id)

    # If the installer ships Playwright Chromium alongside the EXE, use it.
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        try:
            exe_dir = Path(sys.executable).resolve().parent
            # PyInstaller puts bundled data in _internal folder
            shipped = exe_dir / "_internal" / "ms-playwright"
            if shipped.exists():
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(shipped)
        except Exception:
            pass

    from playwright.async_api import async_playwright

    parallel = _load_parallel_scraper()

    preferred_store_id: str | None = None
    slot_status_path = status_dir() / f"slot_{slot_id}.json"
    task_c_failures: dict[int, int] = {}

    # CRITICAL: Stagger slot startup to prevent concurrent fresh sessions
    # PARALLEL staggers worker launches by 5 seconds (orchestrator.py:524)
    # This prevents multiple slots from hitting the same store at once
    if slot_id > 0:
        stagger_delay = slot_id * 5
        print(f"[slot-{slot_id}] Staggering startup by {stagger_delay}s...", flush=True)
        await asyncio.sleep(stagger_delay)

    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        current_store_id: str | None = None

        async def ensure_store(lease: api.Lease):
            nonlocal browser, context, page, current_store_id, preferred_store_id
            if current_store_id == lease.store_id and context and page:   
                return
            if context:
                try:
                    if current_store_id:
                        prev_profile_dir = profiles_dir() / f"store-{current_store_id}"
                        prev_profile_dir.mkdir(parents=True, exist_ok=True)
                        await context.storage_state(path=str(prev_profile_dir / "storage_state.json"))
                    await context.close()
                except Exception:
                    pass
                context = None
                page = None
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
                browser = None
            current_store_id = lease.store_id
            preferred_store_id = lease.store_id

            # IMPORTANT: Profile is PER-STORE only (not per-slot)
            # This matches PARALLEL and allows profile seasoning to benefit all slots
            profile_dir = profiles_dir() / f"store-{lease.store_id}"      
            profile_dir.mkdir(parents=True, exist_ok=True)

            storage_state_path = profile_dir / "storage_state.json"

            # Browser launch config
            # NOTE: UA / header / init-script spoofing caused Akamai blocks in testing.
            launch_kwargs = {
                "headless": False,  # Must be False for anti-bot
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-features=IsolateOrigins,site-per-process", 
                    "--disable-infobars",
                    "--lang=en-US",
                    "--no-default-browser-check",
                ],
            }

            # Prefer system Chrome when available (matches PARALLEL’s most reliable setup).
            explicit_channel = (os.getenv("GLOORBOT_BROWSER_CHANNEL") or "").strip() or None
            prefer_chrome = os.getenv("GLOORBOT_PREFER_CHROME", "1").strip().lower() not in _FALSE_VALUES
            force_bundled = os.getenv("GLOORBOT_FORCE_BUNDLED", "0").strip().lower() not in _FALSE_VALUES
            try_channel = explicit_channel or ("chrome" if (prefer_chrome and not force_bundled) else None)

            # Launch Chromium browser
            print(f"[slot-{slot_id}] Launching browser...", flush=True)
            try:
                if try_channel:
                    try:
                        browser = await p.chromium.launch(channel=try_channel, **launch_kwargs)
                    except Exception:
                        if explicit_channel:
                            raise
                        browser = await p.chromium.launch(**launch_kwargs)
                else:
                    browser = await p.chromium.launch(**launch_kwargs)

                context_kwargs: dict[str, Any] = {
                    "viewport": {"width": 1440, "height": 900},
                    "locale": "en-US",
                }
                if storage_state_path.exists():
                    context_kwargs["storage_state"] = str(storage_state_path)
                context = await browser.new_context(**context_kwargs)

                print(f"[slot-{slot_id}] Context created", flush=True)
            except Exception as e:
                print(f"[slot-{slot_id}] Browser setup failed: {e}", flush=True)
                raise
            page = await context.new_page()

            print(f"[slot-{slot_id}] Browser ready, starting warmup...", flush=True)

            # Do the simple proven warmup (homepage visit + human behavior)
            store_url = _normalize_lowes_url(lease.store_url)
            await parallel.warmup_session(page)
            if not await parallel.set_store_context(page, store_url, lease.store_name):
                print(f"[slot-{slot_id}] Failed to set store {lease.store_name} - aborting lease", flush=True)
                # Close context to force rebuild next time, ensuring fresh retry
                if context:
                    await context.close()
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                    browser = None
                context = None
                page = None
                current_store_id = None
                raise RuntimeError(f"Could not set store context for {lease.store_id}")

            # Persist cookies/session data per-store to reduce repeated "fresh profile" signals.
            try:
                await context.storage_state(path=str(storage_state_path))
            except Exception:
                pass

        lease_failures = 0
        while True:
            lease = None
            try:
                lease = api.lease_next(client_id, preferred_store_id)
                lease_failures = 0
            except Exception:
                lease_failures += 1
                await backoff_sleep(2, lease_failures, 30)
                continue

            if not lease:
                await backoff_sleep(2, max(1, lease_failures), 20)
                continue

            start = time.time()
            eventlog.write(
                "lease_acquired",
                slot_id=slot_id,
                task_id=getattr(lease, "task_id", None),
                store_id=getattr(lease, "store_id", None),
                store_name=getattr(lease, "store_name", None),
                store_url=getattr(lease, "store_url", None),
                category_url=getattr(lease, "category_url", None),
            )
            slot_status_path.write_text(
                json.dumps(
                    {
                        "slot_id": slot_id,
                        "task_id": lease.task_id,
                        "store_id": lease.store_id,
                        "category_url": lease.category_url,
                        "status": "running",
                        "started_at": datetime.utcnow().isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            products_seen = 0
            deals_sent = 0
            try:
                await ensure_store(lease)
                store_info = {
                    "store_id": lease.store_id,
                    "name": lease.store_name,
                    "city": "",
                    "state": "",
                    "url": _normalize_lowes_url(lease.store_url),
                }
                category_url = _normalize_lowes_url(lease.category_url)
                # High-level trace: what we're about to scrape (without pagination noise).
                try:
                    title = await asyncio.wait_for(page.title(), timeout=5.0)
                except Exception:
                    title = None
                eventlog.write(
                    "category_start",
                    slot_id=slot_id,
                    task_id=getattr(lease, "task_id", None),
                    store_id=getattr(lease, "store_id", None),
                    category_url=category_url,
                    page_url=getattr(page, "url", None),
                    title=title,
                )
                products = await asyncio.wait_for(
                    parallel.scrape_category_all_pages(page, category_url, store_info),
                    timeout=MAX_CATEGORY_SECONDS,
                )
                products_seen = len(products)

                deals: list[dict] = []
                for p_item in products:
                    d = _deal_from_product(p_item, lease.category_url)
                    if d:
                        deals.append(d)

                # Bulk submit in one call (deals are already filtered).
                submit_attempts = 0
                batch_id = ""
                while True:
                    try:
                        deals_sent, batch_id = api.submit_deals(client_id, deals, task_id=lease.task_id)
                        break
                    except Exception:
                        submit_attempts += 1
                        if submit_attempts >= 3:
                            raise
                        await backoff_sleep(2, submit_attempts, 30)
                api.lease_complete(client_id, lease.task_id, time.time() - start, products_seen, deals_sent)

                slot_status_path.write_text(
                    json.dumps(
                        {
                            "slot_id": slot_id,
                            "task_id": lease.task_id,
                            "status": "idle",
                            "last_done_at": datetime.utcnow().isoformat(),
                            "products_seen": products_seen,
                            "deals_sent": deals_sent,
                            "last_batch_id": batch_id,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                try:
                    done_title = await asyncio.wait_for(page.title(), timeout=5.0)
                except Exception:
                    done_title = None
                eventlog.write(
                    "category_done",
                    slot_id=slot_id,
                    task_id=getattr(lease, "task_id", None),
                    store_id=getattr(lease, "store_id", None),
                    category_url=category_url,
                    page_url=getattr(page, "url", None),
                    title=done_title,
                    duration_sec=round(time.time() - start, 3),
                    products_seen=products_seen,
                    deals_sent=deals_sent,
                    batch_id=batch_id,
                )
                
                # CRITICAL: Add inter-lease delay to match PARALLEL's pacing
                # PARALLEL sleeps 2.0-4.55s between categories (scraper.py:802-803)
                # Without this, Worker hammers the server too fast → detection
                await asyncio.sleep(2.0 + random.random() * 2.55)
            except Exception as e:
                # If a task keeps landing on a non-listing `/c/` page, it can get
                # re-leased repeatedly and appear "stuck" overnight. After a small
                # number of confirmations, mark the task done (0 products) so the
                # fleet can move on.
                page_url = getattr(page, "url", None)
                raw_category_url = getattr(lease, "category_url", "") or ""
                msg_lower = str(e).lower()
                is_c = (
                    (isinstance(page_url, str) and ("/c/" in page_url) and ("/pl/" not in page_url))
                    or ("/c/" in msg_lower and "redirect" in msg_lower)
                    or (isinstance(raw_category_url, str) and ("/c/" in raw_category_url) and ("/pl/" not in raw_category_url))
                )
                should_abandon = False
                task_id_val = getattr(lease, "task_id", None)
                if is_c and isinstance(task_id_val, int):
                    prev = task_c_failures.get(task_id_val, 0)
                    task_c_failures[task_id_val] = prev + 1
                    # First strike often indicates a persistent bad URL (stale DB task);
                    # allow one retry in case it's a transient redirect, then abandon.
                    should_abandon = task_c_failures[task_id_val] >= 2
                elif is_c:
                    should_abandon = True

                if should_abandon:
                    api.lease_complete(client_id, lease.task_id, time.time() - start, 0, 0)
                    eventlog.write(
                        "task_abandoned_non_pl",
                        slot_id=slot_id,
                        task_id=getattr(lease, "task_id", None),
                        store_id=getattr(lease, "store_id", None),
                        category_url=getattr(lease, "category_url", None),
                        page_url=page_url,
                        error=str(e),
                    )
                else:
                    api.lease_fail(client_id, lease.task_id, time.time() - start)
                try:
                    err_title = await asyncio.wait_for(page.title(), timeout=5.0) if page else None
                except Exception:
                    err_title = None
                eventlog.write(
                    "category_error",
                    slot_id=slot_id,
                    task_id=getattr(lease, "task_id", None),
                    store_id=getattr(lease, "store_id", None),
                    category_url=getattr(lease, "category_url", None),
                    page_url=page_url,
                    title=err_title,
                    duration_sec=round(time.time() - start, 3),
                    error=str(e),
                )
                slot_status_path.write_text(
                    json.dumps(
                        {
                            "slot_id": slot_id,
                            "task_id": lease.task_id,
                            "status": "error",
                            "error": str(e),
                            "trace": traceback.format_exc()[-4000:],
                            "at": datetime.utcnow().isoformat(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                # Block/cooldown behavior: if blocked, wait then rebuild browser.
                msg = str(e).lower()
                if "access denied" in msg or "robot" in msg or "blocked" in msg:
                    # Signal to supervisor that we got blocked
                    _signal_block()
                    try:
                        if page and lease:
                            await _dump_block_artifacts(slot_id=slot_id, lease=lease, page=page, error=e)
                    except Exception:
                        pass
                    try:
                        if context:
                            await context.close()
                        if browser:
                            await browser.close()
                    except Exception:
                        pass
                    browser = None
                    context = None
                    page = None
                    await asyncio_sleep(COOLDOWN_SECONDS)
                else:
                    await backoff_sleep(2, 1, 10)


async def asyncio_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


async def backoff_sleep(base: int, attempt: int, max_seconds: int) -> None:
    import asyncio

    delay = min(max_seconds, base * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0, delay * 0.2)
    await asyncio.sleep(delay + jitter)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--slot-id", type=int, required=True)
    args = parser.parse_args(argv)

    import asyncio

    asyncio.run(_run_slot(args.client_id, args.slot_id))


if __name__ == "__main__":
    main()
