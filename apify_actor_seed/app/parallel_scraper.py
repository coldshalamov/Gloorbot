"""Interactive parallel Lowe's crawler launcher (per-store, all departments).

This GUI reads stores + department URLs from LowesMap.txt and lets you spawn
independent Playwright profiles per store. Each store gets its own mobile
fingerprint to avoid bot correlation. Reuses the working Playwright settings
from the existing launcher (stealth, headed by default, paced navigation).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import tkinter as tk
from tkinter import messagebox, ttk
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from app.anti_blocking import browser_kwargs, clone_profile, dedupe_preserve_order, nav_semaphore, pick_device, profile_dir
from app.logging_config import get_logger
from app.multi_store import (
    Store,
    filter_departments,
    human_pause,
    parse_lowes_map,
)
from app.retailers.lowes import scrape_category, set_store_context
from app.playwright_env import apply_stealth, launch_browser
import app.selectors as selectors
from app.extractors.dom_utils import human_wait
from app.storage.db import get_engine, init_db_safe, make_session
from app.storage import repo
from app.storage.models_sql import Observation

LOGGER = get_logger(__name__)

DEFAULT_NAV_CAP = 1  # safer default to reduce velocity
DEFAULT_WAIT_SECONDS = (3.0, 7.0)  # match earlier pacing
MAP_PATH = Path("..") / "LowesMap.txt"
BASE_PROFILE = Path(os.getenv("CHEAPSKATER_USER_DATA_DIR") or ".playwright-profile")
BASE_PROFILE.mkdir(parents=True, exist_ok=True)

# Database setup (same as launch.bat crawler)
SQLITE_PATH = Path("orwa_lowes.sqlite")
engine = get_engine(str(SQLITE_PATH))
init_db_safe(engine)
session_factory = make_session(engine)


@dataclass(frozen=True)
class StoreChoice:
    label: str
    store: Store


def _store_label(store: Store) -> str:
    """Human-ish label derived from the store URL slug."""

    slug = store.url.rsplit("/store/", 1)[-1]
    parts = slug.split("/")
    city = parts[0].replace("-", " ").title() if parts else slug
    return f"{store.id} - {city}"


def _log_product_to_db(product: dict[str, Any], store: Store, log: Callable[[str], None]) -> None:
    """Log a single product to SQLite database in real-time (like launch.bat crawler)."""

    session = None
    try:
        session = session_factory()

        # Extract product fields
        sku = (product.get("sku") or "").strip()
        title = (product.get("title") or "").strip()
        category = (product.get("category") or "").strip() or "Uncategorised"
        product_url = (product.get("product_url") or "").strip()
        image_url = (product.get("image_url") or "").strip() or None
        price = product.get("price")
        price_was = product.get("price_was")
        pct_off = product.get("pct_off")
        availability = (product.get("availability") or "").strip() or None
        clearance = product.get("clearance", False)

        store_id = product.get("store_id") or store.id
        store_name = product.get("store_name") or f"Lowe's {store.id}"
        store_zip = product.get("zip") or store.id

        if not sku or not title or not product_url:
            log(f"[{store.id}] Skipping product with missing data: {title}")
            return

        ts_now = datetime.now(timezone.utc)

        # Upsert store
        repo.upsert_store(
            session,
            store_id,
            store_name,
            zip_code=store_zip,
            city=None,
            state="WA",  # Assume WA/OR based on config
        )

        # Upsert item
        repo.upsert_item(
            session,
            sku,
            "lowes",
            title,
            category,
            product_url,
            image_url=image_url,
        )

        # Insert observation
        obs_model = Observation(
            ts_utc=ts_now,
            store_id=store_id,
            sku=sku,
            retailer="lowes",
            store_name=store_name,
            zip=store_zip,
            title=title,
            category=category,
            product_url=product_url,
            image_url=image_url,
            price=price,
            price_was=price_was,
            pct_off=pct_off,
            clearance=clearance,
            availability=availability,
        )
        repo.insert_observation(session, obs_model)

        # Update price history
        repo.update_price_history(
            session,
            retailer="lowes",
            store_id=store_id,
            sku=sku,
            title=title,
            category=category,
            ts_utc=ts_now,
            price=price,
            price_was=price_was,
            pct_off=pct_off,
            availability=availability,
            product_url=product_url,
            image_url=image_url,
            clearance=clearance,
        )

        session.commit()

    except Exception as exc:
        LOGGER.warning(f"[{store.id}] Failed to log product {product.get('sku')}: {exc}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()


async def _run_single_store(
    store: Store,
    departments: list[str],
    *,
    nav_cap: int,
    human_wait_bounds: tuple[float, float],
    device_name: str | None,
    log: Callable[[str], None],
) -> None:
    """Launch a headed persistent profile (same as launch.bat) and sweep all departments.

    This function is resilient: if the browser crashes, it will restart and continue
    where it left off. It tracks completed departments to avoid re-scraping.
    """

    # Track which departments we've successfully completed
    completed_departments = set()
    max_browser_restarts = 3
    browser_restart_count = 0

    while browser_restart_count < max_browser_restarts:
        try:
            await _run_store_with_browser(
                store=store,
                departments=departments,
                completed_departments=completed_departments,
                nav_cap=nav_cap,
                human_wait_bounds=human_wait_bounds,
                device_name=device_name,
                log=log,
            )
            # If we get here, we finished successfully
            log(f"[{store.id}] Completed all departments successfully!")
            break
        except Exception as exc:
            browser_restart_count += 1
            log(f"[{store.id}] Browser crashed or critical error: {exc}")
            if browser_restart_count < max_browser_restarts:
                log(f"[{store.id}] Restarting browser (attempt {browser_restart_count}/{max_browser_restarts})...")
                await asyncio.sleep(5)  # Wait before restart
            else:
                log(f"[{store.id}] Max restart attempts reached. Giving up.")
                raise


async def _run_store_with_browser(
    store: Store,
    departments: list[str],
    completed_departments: set[str],
    nav_cap: int,
    human_wait_bounds: tuple[float, float],
    device_name: str | None,
    log: Callable[[str], None],
) -> None:
    """Run store scraping with a single browser instance."""

    async with async_playwright() as p:
        apply_stealth(p)
        chosen_name, descriptor = pick_device(p)
        if device_name and device_name in p.devices:
            chosen_name = device_name
            descriptor = p.devices[device_name]

        log(f"[{store.id}] Using device '{chosen_name}' (simulating real mobile user)")

        # Create unique persistent profile for this store (looks like different person)
        store_profile = profile_dir(Path(".playwright-parallel-profiles"), store.id)
        log(f"[{store.id}] Using persistent profile: {store_profile}")

        # Use EXACT SAME launch method as working single-browser launcher
        from app.playwright_env import launch_kwargs
        launch_opts = launch_kwargs()
        launch_opts["headless"] = False  # Override to headed

        browser = None
        context = None
        cleanup_success = False
        
        try:
            # Launch with persistent profile using WORKING method
            log(f"[{store.id}] Launching browser with persistent profile...")
            context = await p.chromium.launch_persistent_context(str(store_profile), **launch_opts)
            browser = context.browser
            log(f"[{store.id}] Browser launched with persistent profile")

            page = await context.new_page()
            nav_sem = nav_semaphore(nav_cap)

            # SIMPLE SOLUTION: Just visit store page and click "Set as My Store" button (best-effort).
            # Use semaphore to prevent all parallel browsers from hitting at once
            log(f"[{store.id}] Loading store page...")
            try:
                async with nav_sem:  # CRITICAL: Throttle simultaneous navigations
                    await page.goto(store.url, wait_until="domcontentloaded", timeout=60_000)
                    await page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception as exc:
                log(f"[{store.id}] Store page load slow ({exc}); continuing anyway")
            await human_wait(1000, 2000, obey_policy=False)

            log(f"[{store.id}] Clicking 'Set as My Store' button...")
            button_clicked = False
            button_selectors = [
                "button:has-text('Set as My Store')",
                "button:has-text('Set Store')",
                "button:has-text('Make This My Store')",
                "a:has-text('Set as My Store')",
                "[data-testid*='set-store']",
                "[data-test-id*='set-store']",
                "button:has-text('My Store')",
            ]

            for selector in button_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=8000)
                    if button:
                        await button.click()
                        button_clicked = True
                        log(f"[{store.id}] Clicked button via selector: {selector}")
                        break
                except Exception:
                    continue

            if not button_clicked:
                log(f"[{store.id}] WARNING: Could not find 'Set as My Store' button, continuing anyway")

            try:
                await context.add_cookies(
                    [{"name": "sn", "value": store.id, "domain": ".lowes.com", "path": "/"}]
                )
                log(f"[{store.id}] Added sn cookie for store context")
            except Exception as exc:
                log(f"[{store.id}] Could not add sn cookie: {exc}")

            await human_wait(1200, 2200, obey_policy=False)

            store_badge_selector = getattr(selectors, "STORE_BADGE", None)
            if store_badge_selector:
                try:
                    badge = await page.wait_for_selector(store_badge_selector, timeout=6000)
                    if badge:
                        badge_text = await badge.inner_text()
                        log(f"[{store.id}] Store badge: {badge_text}")
                except Exception:
                    log(f"[{store.id}] Could not verify store badge; proceeding")

            log(f"[{store.id}] Starting to crawl departments (already completed: {len(completed_departments)})...")
            results: list[dict[str, object]] = []

            # Use WORKING pagination logic from lowes.py
            for dept_url in departments:
                dept_name = dept_url.split("/")[-1] if "/" in dept_url else dept_url

                # Skip already completed departments (from previous browser session)
                if dept_url in completed_departments:
                    log(f"[{store.id}] Skipping {dept_name} (already completed)")
                    continue

                await human_pause(human_wait_bounds)

                # Try this department with retries on failure
                max_dept_retries = 3
                for attempt in range(max_dept_retries):
                    try:
                        async with nav_sem:
                            log(f"[{store.id}] Starting {dept_name}... (attempt {attempt+1}/{max_dept_retries})")

                            # Detect if page crashed (common Chrome issue - "Aw, Snap!" or "Out of Memory")
                            try:
                                await page.evaluate("() => 1 + 1")  # Simple test
                            except Exception as page_exc:
                                log(f"[{store.id}] Page crashed ({page_exc})! Creating new page...")
                                try:
                                    page = await context.new_page()
                                    # Re-set store context for new page
                                    await page.goto(store.url, wait_until="domcontentloaded", timeout=30_000)
                                    await context.add_cookies([{"name": "sn", "value": store.id, "domain": ".lowes.com", "path": "/"}])
                                    log(f"[{store.id}] New page created and store context restored")
                                except Exception as recovery_exc:
                                    log(f"[{store.id}] Failed to recover page ({recovery_exc}). Browser will restart.")
                                    raise  # Trigger browser restart

                            # Call scrape_category from working crawler
                            products = await scrape_category(
                                page=page,
                                url=dept_url,
                                category_name=dept_name,
                                zip_code=store.id,
                                store_id=store.id,
                                clearance_threshold=0.0,  # Get all items
                            )

                            if products:
                                # Log each product to database IN REAL-TIME (like launch.bat crawler)
                                log(f"[{store.id}] {dept_name} -> {len(products)} products, logging to database...")
                                for product in products:
                                    _log_product_to_db(product, store, log)

                                # Also keep JSON for backup
                                results.append({"department": dept_url, "store_id": store.id, "products": products})
                                log(f"[{store.id}] {dept_name} -> {len(products)} products logged to database")
                            else:
                                log(f"[{store.id}] No products on {dept_name}")

                            # Mark as completed
                            completed_departments.add(dept_url)
                            break  # Success, move to next department

                    except PlaywrightTimeoutError as exc:
                        log(f"[{store.id}] Timeout on {dept_name} (attempt {attempt+1}): {exc}")
                        if attempt < max_dept_retries - 1:
                            log(f"[{store.id}] Retrying {dept_name}...")
                            await asyncio.sleep(3)  # Wait before retry
                        else:
                            log(f"[{store.id}] Giving up on {dept_name} after {max_dept_retries} attempts")
                            completed_departments.add(dept_url)  # Mark as completed to avoid infinite retry
                    except Exception as exc:
                        log(f"[{store.id}] Error on {dept_name} (attempt {attempt+1}): {exc}")
                        if attempt < max_dept_retries - 1:
                            log(f"[{store.id}] Retrying {dept_name}...")
                            await asyncio.sleep(3)
                        else:
                            log(f"[{store.id}] Giving up on {dept_name} after {max_dept_retries} attempts")
                            completed_departments.add(dept_url)

            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out_dir = Path("outputs/stores")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"store_{store.id}_{ts}.json"
            out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
            log(f"[{store.id}] Wrote {out_path} with {len(results)} departments")

        except Exception as exc:
            import traceback
            log(f"[{store.id}] CRITICAL ERROR in browser operations: {exc}")
            log(f"[{store.id}] Traceback: {traceback.format_exc()}")
            raise
        finally:
            # Ensure cleanup happens in ALL cases - success or failure
            cleanup_success = False
            try:
                if context:
                    log(f"[{store.id}] Closing browser context...")
                    await context.close()
                    cleanup_success = True
                    log(f"[{store.id}] Browser context closed successfully")
                elif browser:
                    log(f"[{store.id}] Closing browser...")
                    await browser.close()
                    cleanup_success = True
                    log(f"[{store.id}] Browser closed successfully")
            except Exception as cleanup_exc:
                log(f"[{store.id}] ERROR during cleanup: {cleanup_exc}")

            if cleanup_success:
                log(f"[{store.id}] Browser cleanup verified - no leakage")
            else:
                log(f"[{store.id}] WARNING: Browser cleanup may have failed - potential leakage")


class ParallelUI:
    def __init__(self, root: tk.Tk, map_path: Path) -> None:
        self.root = root
        self.root.title("CheapSkater Parallel Lowe's Crawler")
        self.root.geometry("720x380")

        self.map_path = map_path
        self.stores, departments = parse_lowes_map(map_path)
        self.departments = filter_departments(departments, max_count=None)
        self.store_choices = [StoreChoice(label=_store_label(s), store=s) for s in self.stores]

        self._running: set[str] = set()
        self._build_layout()

    def _build_layout(self) -> None:
        padding = {"padx": 8, "pady": 6}

        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, **padding)
        ttk.Label(top, text=f"Map: {self.map_path}").pack(side=tk.LEFT)
        ttk.Label(top, text=f"Departments: {len(self.departments)}").pack(side=tk.LEFT, padx=12)

        store_frame = ttk.Frame(self.root)
        store_frame.pack(fill=tk.X, **padding)
        ttk.Label(store_frame, text="Store:").pack(side=tk.LEFT)
        self.store_var = tk.StringVar()
        self.store_combo = ttk.Combobox(
            store_frame,
            textvariable=self.store_var,
            values=[c.label for c in self.store_choices],
            width=45,
        )
        self.store_combo.pack(side=tk.LEFT, padx=6)
        if self.store_choices:
            self.store_combo.current(0)

        ttk.Label(store_frame, text="Nav cap:").pack(side=tk.LEFT, padx=6)
        self.nav_cap_var = tk.StringVar(value=str(DEFAULT_NAV_CAP))
        ttk.Entry(store_frame, textvariable=self.nav_cap_var, width=4).pack(side=tk.LEFT)

        ttk.Label(store_frame, text="Wait (min-max sec):").pack(side=tk.LEFT, padx=6)
        self.wait_min_var = tk.StringVar(value=str(DEFAULT_WAIT_SECONDS[0]))
        self.wait_max_var = tk.StringVar(value=str(DEFAULT_WAIT_SECONDS[1]))
        ttk.Entry(store_frame, textvariable=self.wait_min_var, width=4).pack(side=tk.LEFT)
        ttk.Entry(store_frame, textvariable=self.wait_max_var, width=4).pack(side=tk.LEFT)

        ttk.Button(store_frame, text="Launch store crawler", command=self.launch_store).pack(
            side=tk.LEFT, padx=12
        )

        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, **padding)
        self.log = tk.Text(log_frame, height=12, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.root, text="Each store uses its own Playwright profile + mobile fingerprint.").pack(
            side=tk.TOP, pady=4
        )

    def _append_log(self, message: str) -> None:
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def _log_threadsafe(self, message: str) -> None:
        self.root.after(0, self._append_log, message)
        LOGGER.info(message)

    def _selected_store(self) -> Optional[Store]:
        label = self.store_var.get()
        for choice in self.store_choices:
            if choice.label == label:
                return choice.store
        return None

    def launch_store(self) -> None:
        store = self._selected_store()
        if store is None:
            messagebox.showerror("No store selected", "Please choose a store from the dropdown.")
            return

        if store.id in self._running:
            messagebox.showinfo("Already running", f"Store {store.id} is already running.")
            return

        try:
            nav_cap = int(self.nav_cap_var.get() or DEFAULT_NAV_CAP)
        except ValueError:
            nav_cap = DEFAULT_NAV_CAP
        try:
            wait_min = float(self.wait_min_var.get() or DEFAULT_WAIT_SECONDS[0])
            wait_max = float(self.wait_max_var.get() or DEFAULT_WAIT_SECONDS[1])
        except ValueError:
            wait_min, wait_max = DEFAULT_WAIT_SECONDS

        # Filter departments using the working filter logic (already removes save-now, deals, etc.)
        departments = filter_departments(self.departments, None)
        departments = dedupe_preserve_order(departments)

        self._running.add(store.id)
        self._log_threadsafe(f"[{store.id}] Starting crawl with {len(departments)} departments")

        thread = threading.Thread(
            target=self._launch_thread,
            args=(store, departments, nav_cap, (wait_min, wait_max)),
            daemon=True,
        )
        thread.start()

    def _launch_thread(
        self,
        store: Store,
        departments: list[str],
        nav_cap: int,
        wait_bounds: tuple[float, float],
    ) -> None:
        async def runner() -> None:
            try:
                await _run_single_store(
                    store,
                    departments,
                    nav_cap=nav_cap,
                    human_wait_bounds=wait_bounds,
                    device_name=None,
                    log=self._log_threadsafe,
                )
            finally:
                self._running.discard(store.id)
                self._log_threadsafe(f"[{store.id}] Finished")

        asyncio.run(runner())


def main() -> None:
    if not MAP_PATH.exists():
        raise SystemExit(f"LowesMap.txt not found at {MAP_PATH}")

    root = tk.Tk()
    ui = ParallelUI(root, MAP_PATH)
    ui._append_log("Loaded map and departments. Pick a store and launch to start crawling.")
    root.mainloop()


if __name__ == "__main__":
    main()
