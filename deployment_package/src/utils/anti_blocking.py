"""Helper utilities for spreading concurrent Playwright crawlers across distinct browser
fingerprints without tripping the bot defenses that the main crawler already avoids."""

from __future__ import annotations

import asyncio
import os
import random
import secrets
import shutil
from pathlib import Path
from typing import Iterable, Sequence

from app.playwright_env import headless_enabled, launch_kwargs

# Prefer mobile personas to mirror the working launcher and reduce bot pressure.
MOBILE_DEVICE_POOL: tuple[str, ...] = (
    "Pixel 5",
    "Pixel 7",
    "Galaxy S9+",
    "Galaxy S20",
    "iPhone 11",
    "iPhone 12",
    "iPhone 13",
    "iPhone 14",
)

TIMEZONES: tuple[str, ...] = (
    "America/Los_Angeles",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
)

LOCALES: tuple[str, ...] = (
    "en-US",
    "en-GB",
    "en-CA",
    "en-AU",
)

COLOR_SCHEMES: tuple[str, ...] = ("light", "dark")


def _normalize_device_payload(payload: dict[str, object]) -> dict[str, object]:
    """Standardize Playwright's device descriptor keys."""

    normalized = payload.copy()
    if "userAgent" in normalized and "user_agent" not in normalized:
        normalized["user_agent"] = normalized.pop("userAgent")
    return normalized


def pick_device(playwright, pool: Sequence[str] | None = None) -> tuple[str, dict[str, object]]:
    """Return a (device_name, descriptor) tuple with randomized human-like traits."""

    devices = playwright.devices
    pool = tuple(pool or MOBILE_DEVICE_POOL)
    usable_pool = [entry for entry in pool if entry in devices]
    if not usable_pool:
        usable_pool = [name for name in devices.keys() if "Pixel" in name or "iPhone" in name] or list(
            devices.keys()
        )

    name = random.choice(usable_pool)
    descriptor = _normalize_device_payload(devices[name])
    descriptor.setdefault("locale", random.choice(LOCALES))
    descriptor.setdefault("timezone_id", random.choice(TIMEZONES))
    descriptor.setdefault("color_scheme", random.choice(COLOR_SCHEMES))
    return name, descriptor


def nav_semaphore(cap: int) -> asyncio.Semaphore:
    """Bound simultaneous navigations across all store crawlers."""

    return asyncio.Semaphore(max(1, int(cap or 1)))


def profile_dir(root: Path, store_id: str) -> Path:
    """Return a unique, per-store profile directory for added fingerprint variance."""

    path = root / f"store_{store_id}_{secrets.token_hex(2)}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def clone_profile(src: Path | None, dest: Path) -> None:
    """
    Copy a base persistent profile into *dest* when available.
    Best-effort: skip if src is missing or empty.
    """

    if src is None:
        return
    try:
        if src.is_dir() and any(src.iterdir()):
            shutil.copytree(src, dest, dirs_exist_ok=True)
    except Exception:
        # Profile seeding is optional; swallow errors to avoid blocking the crawl.
        pass


def browser_kwargs() -> dict[str, object]:
    """Merge global launch kwargs with headless override."""

    return {**launch_kwargs(), "headless": headless_enabled()}


def dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    """Remove duplicates while keeping first-seen ordering."""

    seen: dict[str, None] = {}
    ordered: list[str] = []
    for entry in items:
        if entry in seen:
            continue
        seen[entry] = None
        ordered.append(entry)
    return ordered
