from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from . import api
from .paths import profiles_dir, status_dir


DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "0.50"))
COOLDOWN_SECONDS = int(os.getenv("BLOCK_COOLDOWN_SECONDS", "300"))


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
    # Normalize weird newlines like "$\n42\n.29"
    compact = re.sub(r"\s+", "", text)
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
    price_now = _to_float_price(str(p.get("price", "")))
    was_price = _to_float_price(str(p.get("was_price", "")))
    if not price_now or not was_price or was_price <= 0:
        return None
    # Ensure price is actually discounted (price < was_price)
    if price_now >= was_price:
        return None
    pct_off = (was_price - price_now) / was_price
    if pct_off < DEAL_THRESHOLD:
        return None
    return {
        "store_id": p.get("store_id"),
        "store_name": p.get("store_name"),
        "category_url": category_url,
        "product_url": p.get("url"),
        "title": p.get("title", "")[:2048],
        "price": float(price_now),
        "was_price": float(was_price),
        "pct_off": float(round(pct_off, 4)),
        "found_at": datetime.utcnow().isoformat(),
    }


async def _run_slot(client_id: str, slot_id: int) -> None:
    # If the installer ships Playwright Chromium alongside the EXE, use it.
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        try:
            exe_dir = Path(sys.executable).resolve().parent
            shipped = exe_dir / "ms-playwright"
            if shipped.exists():
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(shipped)
        except Exception:
            pass

    from playwright.async_api import async_playwright

    parallel = _load_parallel_scraper()

    preferred_store_id: str | None = None
    slot_status_path = status_dir() / f"slot_{slot_id}.json"

    async with async_playwright() as p:
        context = None
        page = None
        current_store_id: str | None = None

        async def ensure_store(lease: api.Lease):
            nonlocal context, page, current_store_id, preferred_store_id
            if current_store_id == lease.store_id and context and page:
                return
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            current_store_id = lease.store_id
            preferred_store_id = lease.store_id

            profile_dir = profiles_dir() / f"store-{lease.store_id}" / f"slot-{slot_id}"
            profile_dir.mkdir(parents=True, exist_ok=True)

            # Try system Chrome channel first (best if installed), else Playwright Chromium.
            launch_kwargs = {
                "headless": False,
                "viewport": {"width": 1440, "height": 900},
                "locale": "en-US",
                "timezone_id": "America/Los_Angeles",
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-gpu",
                    "--no-sandbox",
                ],
            }
            try:
                context = await p.chromium.launch_persistent_context(str(profile_dir), channel="chrome", **launch_kwargs)
            except Exception:
                context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()

            await parallel.warmup_session(page)
            await parallel.set_store_context(page, lease.store_url, lease.store_name)

        while True:
            lease = None
            try:
                lease = api.lease_next(client_id, preferred_store_id)
            except Exception:
                await asyncio_sleep(10)
                continue

            if not lease:
                await asyncio_sleep(10)
                continue

            start = time.time()
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
                    "url": lease.store_url,
                }
                products = await parallel.scrape_category_all_pages(page, lease.category_url, store_info)
                products_seen = len(products)

                deals: list[dict] = []
                for p_item in products:
                    d = _deal_from_product(p_item, lease.category_url)
                    if d:
                        deals.append(d)

                # Bulk submit in one call (deals are already filtered).
                deals_sent = api.submit_deals(client_id, deals)
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
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except Exception as e:
                api.lease_fail(client_id, lease.task_id, time.time() - start)
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
                    try:
                        if context:
                            await context.close()
                    except Exception:
                        pass
                    context = None
                    page = None
                    await asyncio_sleep(COOLDOWN_SECONDS)
                else:
                    await asyncio_sleep(5)


async def asyncio_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--slot-id", type=int, required=True)
    args = parser.parse_args(argv)

    import asyncio

    asyncio.run(_run_slot(args.client_id, args.slot_id))


if __name__ == "__main__":
    main()
