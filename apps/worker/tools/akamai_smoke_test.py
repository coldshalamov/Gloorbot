from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright


def _import_worker_helpers():
    try:
        from gloorbot_worker.paths import profiles_dir
        from gloorbot_worker.slot_worker import _load_parallel_scraper
    except ModuleNotFoundError:
        # Allow running directly from the repo without installing `gloorbot-worker`.
        worker_root = Path(__file__).resolve().parents[1]  # apps/worker
        sys.path.insert(0, str(worker_root / "src"))
        from gloorbot_worker.paths import profiles_dir
        from gloorbot_worker.slot_worker import _load_parallel_scraper
    return profiles_dir, _load_parallel_scraper


DEFAULT_STORE_ID = "0061"
DEFAULT_STORE_URL = "https://www.lowes.com/store/WA-Arlington/0061"
DEFAULT_STORE_NAME = "Arlington, WA"
DEFAULT_CATEGORY_URL = "https://www.lowes.com/pl/Extension-cords/4294934373"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual smoke test for Lowe's Akamai blocks.")
    parser.add_argument("--store-id", default=DEFAULT_STORE_ID)
    parser.add_argument("--store-url", default=DEFAULT_STORE_URL)
    parser.add_argument("--store-name", default=DEFAULT_STORE_NAME)
    parser.add_argument("--category-url", default=DEFAULT_CATEGORY_URL)
    parser.add_argument("--channel", default=os.getenv("GLOORBOT_BROWSER_CHANNEL", "").strip() or None)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--screenshot", default=None, help="Optional screenshot path.")
    parser.add_argument(
        "--scrape-pages",
        type=int,
        default=0,
        help="If set, runs PARALLEL scrape_category_page for N pages (slow).",
    )
    parser.add_argument(
        "--no-storage-state",
        action="store_true",
        help="Disable loading/saving per-store storage_state.json.",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    profiles_dir, _load_parallel_scraper = _import_worker_helpers()
    parallel = _load_parallel_scraper()

    profile_dir = profiles_dir() / f"store-{args.store_id}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path = profile_dir / "storage_state.json"

    async with async_playwright() as p:
        launch_kwargs: dict[str, object] = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=en-US",
                "--no-default-browser-check",
            ],
        }
        if args.channel:
            launch_kwargs["channel"] = args.channel

        browser = await p.chromium.launch(**launch_kwargs)
        context_kwargs: dict[str, object] = {
            "viewport": {"width": args.width, "height": args.height},
            "locale": "en-US",
        }
        if (not args.no_storage_state) and storage_state_path.exists():
            context_kwargs["storage_state"] = str(storage_state_path)

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            await parallel.warmup_session(page)
            ok = await parallel.set_store_context(page, args.store_url, args.store_name)
            print(f"STORE_SET: {ok}", flush=True)

            await page.goto(args.category_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)
            title = await page.title()
            print(f"TITLE: {title}", flush=True)

            if args.screenshot:
                screenshot_path = Path(args.screenshot).expanduser().resolve()
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"SCREENSHOT: {screenshot_path}", flush=True)

            lowered = title.lower()
            if "access denied" in lowered or "robot" in lowered or "blocked" in lowered:
                return 2

            if args.scrape_pages and args.scrape_pages > 0:
                store_info = {
                    "store_id": args.store_id,
                    "name": args.store_name,
                    "city": "",
                    "state": "",
                    "url": args.store_url,
                }
                for page_num in range(1, args.scrape_pages + 1):
                    products = await parallel.scrape_category_page(page, args.category_url, store_info, page_num)
                    print(f"SCRAPE_PAGE_{page_num}: {len(products)} products", flush=True)
            return 0
        finally:
            if not args.no_storage_state:
                try:
                    await context.storage_state(path=str(storage_state_path))
                except Exception:
                    pass
            await context.close()
            await browser.close()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
