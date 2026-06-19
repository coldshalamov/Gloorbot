"""
Performance Settings Module for Gloorbot Worker

This module provides tunable performance parameters that can be adjusted
via the GUI or environment variables. Settings are persisted to disk.

CRITICAL AKAMAI NOTES:
- DO NOT block /_sec/ scripts (Akamai bot detection)
- DO NOT run headless (instant block)
- DO NOT inject stealth scripts (makes detection worse)
- Images can be blocked but DOM must still render structure
- Audio/video can safely be blocked
- Fonts can be blocked (slight visual difference, big bandwidth savings)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# Handle PyInstaller frozen executable
import sys
if getattr(sys, 'frozen', False):
    from gloorbot_worker.paths import config_dir
else:
    from .paths import config_dir


# Current settings schema version. Bump when a defaults change needs a one-time
# migration of already-saved configs (see PerformanceSettings.load).
SETTINGS_VERSION = 2


def _settings_path() -> Path:
    """Get the path to the settings JSON file."""
    return config_dir() / "performance_settings.json"


@dataclass
class PerformanceSettings:
    """
    Tunable performance parameters for the Gloorbot Worker.

    These settings balance speed vs. Akamai detection risk.
    Default values are conservative (proven not to trigger blocks).
    """

    # === BROWSER POOL SETTINGS ===
    # Fixed browser count (0 = dynamic scaling based on CPU/memory)
    fixed_browser_count: int = 0

    # Maximum browsers when using dynamic scaling. 6 is the top of the documented
    # safe range for one IP/machine; the dynamic scaler only reaches it if CPU/RAM
    # allow, and block-backoff reduces it automatically if Akamai pushes back.
    # Do not raise above 6 on a single IP. Conservative caps far lower.
    max_browsers: int = 6

    # Minimum browsers (always keep at least this many running)
    min_browsers: int = 1

    # === TIMING SETTINGS (in seconds) ===
    # Click delay range: random delay before clicking elements
    # Lower = faster but higher risk of detection
    click_delay_min: float = 0.1
    click_delay_max: float = 0.4

    # Page navigation delay range: settle wait AFTER a page loads (before the
    # human mouse/scroll pass). This is "dead time" — the human interaction
    # itself is paced separately and is never throttled. Floors stay >=1s to
    # remain human-plausible.
    # CRITICAL: Too fast triggers Akamai's "inhuman speed" detection
    nav_delay_min: float = 1.2
    nav_delay_max: float = 2.8

    # Pre-navigation settle: dead-wait BEFORE navigating to the next page.
    prenav_delay_min: float = 1.0
    prenav_delay_max: float = 2.4

    # Pre-scrape settle: dead-wait after the human pass, just before reading DOM.
    prescrape_delay_min: float = 1.0
    prescrape_delay_max: float = 2.0

    # Bounded networkidle timeout (ms). Lowe's is beacon-heavy and rarely reaches
    # true networkidle, so the old 8-10s waits almost always elapsed in full.
    # This caps that dead time; it is NOT a human-pacing signal.
    networkidle_timeout_ms: int = 3500

    # Max lazy-load scroll passes per page before reading the DOM. With early
    # exit on, the scraper stops once the grid stops growing, so this is the
    # ceiling; with early exit off it is the exact (unconditional) scroll count.
    hydration_max_scrolls: int = 6

    # Allow the hydration scroll pass to exit early once the product grid has
    # finished lazy-loading. Off = always run the full hydration_max_scrolls pass
    # (the original, pre-optimization behavior). Conservative preset turns it off.
    hydration_early_exit: bool = True

    # Inter-lease delay: delay between finishing one task and starting next.
    # Dead time between tasks; each new category also does its own pre-nav settle.
    inter_lease_delay_min: float = 1.5
    inter_lease_delay_max: float = 3.0

    # Warmup duration: time spent on homepage building trust
    warmup_delay_min: float = 3.5
    warmup_delay_max: float = 5.5

    # Store context delay: time after setting store
    store_delay_min: float = 2.0
    store_delay_max: float = 3.0

    # === RESOURCE BLOCKING ===
    # Block images: saves ~60-70% bandwidth and page-load time. The DOM (incl.
    # <img> src/data-src attributes the scraper reads) is unaffected — only the
    # pixel download is aborted, so image_url extraction still works. Documented
    # as Akamai-safe. Default ON for speed; Conservative preset turns it off.
    block_images: bool = True

    # Block fonts: saves ~5-10% bandwidth/time, text content unaffected (glyphs
    # don't affect inner_text/aria-label extraction). Documented as Akamai-safe.
    block_fonts: bool = True

    # Block media (audio/video): safe to block, rarely used on Lowe's
    block_media: bool = True

    # Block analytics/tracking (except Akamai): saves bandwidth + faster
    # NEVER blocks /_sec/ which is Akamai's bot detection
    block_analytics: bool = True

    # Abort image loading after DOM renders (hybrid approach)
    # Fetches enough to satisfy Akamai but doesn't fully render
    abort_images_after_dom: bool = False

    # === VIEWPORT SETTINGS ===
    # Smaller viewport = faster rendering, less compositing memory per window.
    # 1280x720 is ~37% fewer pixels than 1440x900 and is a completely ordinary
    # laptop size (no detection signal). Does not affect which products are
    # scraped (extraction reads the full DOM, not just the visible area).
    viewport_width: int = 1280
    viewport_height: int = 720

    # === BROWSER LAUNCH ARGS ===
    # These are safe optimizations that don't trigger detection
    disable_gpu: bool = False  # True = faster on low-end machines
    disable_dev_shm: bool = True  # Prevents /dev/shm crashes in containers
    disable_background_networking: bool = True  # Prevents idle traffic
    disable_background_timer_throttling: bool = True
    disable_backgrounding_occluded_windows: bool = True
    disable_renderer_backgrounding: bool = True
    memory_pressure_off: bool = True  # Prevents OOM crashes

    # Lean browser flags: disable Chrome background subsystems (sync, component
    # updates, crash reporting, domain-reliability beacons, etc.) that consume
    # CPU/RAM but are irrelevant to scraping. These are fingerprint-NEUTRAL — they
    # don't change any page-visible signal (navigator.*, WebGL, canvas), so Akamai
    # can't see them — and they help each window stay light enough to run more in
    # parallel. Conservative preset turns them off.
    lean_browser_flags: bool = True

    # === CONCURRENT PAGES PER BROWSER ===
    # More pages = faster but higher memory and detection risk
    # PARALLEL uses 4, which is proven safe
    pages_per_browser: int = 4

    # === STAGGER SETTINGS ===
    # Delay between launching slots to prevent concurrent fresh sessions
    slot_stagger_seconds: int = 5

    # === SCHEMA VERSION ===
    # Bumped when defaults change in a way that needs a one-time migration of
    # existing saved configs. v2 = performance optimization (safe-fast defaults).
    settings_version: int = SETTINGS_VERSION

    # === PRESETS ===
    @classmethod
    def conservative(cls) -> "PerformanceSettings":
        """
        Conservative preset: Prioritizes avoiding blocks over speed.

        Rollback safety net: restores the original detection-relevant behavior —
        the slower per-page settles, the longer networkidle bound, the full
        unconditional hydration scroll (hydration_early_exit off), and image/font
        blocking off. Use this if you're getting blocked frequently.
        """
        return cls(
            fixed_browser_count=3,
            click_delay_min=0.2,
            click_delay_max=0.6,
            nav_delay_min=2.0,
            nav_delay_max=4.55,
            prenav_delay_min=1.5,
            prenav_delay_max=3.9,
            prescrape_delay_min=1.5,
            prescrape_delay_max=3.25,
            networkidle_timeout_ms=8000,
            hydration_early_exit=False,  # full unconditional scroll pass (old behavior)
            inter_lease_delay_min=3.0,
            inter_lease_delay_max=6.0,
            block_images=False,
            block_fonts=False,
            lean_browser_flags=False,  # original minimal browser-arg set
            viewport_width=1440,
            viewport_height=900,
        )

    @classmethod
    def balanced(cls) -> "PerformanceSettings":
        """
        Balanced preset: the default, optimized for speed while staying within
        Akamai-safe limits (image/font blocking on, bounded networkidle, trimmed
        dead-time settles with >=1s floors, early-exit lazy-load). Human mouse/
        scroll behavior is unchanged from the original.
        """
        return cls()  # Defaults are the safe-fast profile

    @classmethod
    def aggressive(cls) -> "PerformanceSettings":
        """
        Aggressive preset: Prioritizes speed, higher block risk.
        Use with caution - may trigger Akamai if IP is flagged.
        """
        return cls(
            fixed_browser_count=5,
            click_delay_min=0.05,
            click_delay_max=0.2,
            nav_delay_min=1.0,
            nav_delay_max=2.5,
            prenav_delay_min=0.8,
            prenav_delay_max=1.8,
            prescrape_delay_min=0.8,
            prescrape_delay_max=1.6,
            networkidle_timeout_ms=3000,
            hydration_max_scrolls=5,
            inter_lease_delay_min=1.0,
            inter_lease_delay_max=2.5,
            warmup_delay_min=2.0,
            warmup_delay_max=3.5,
            block_images=True,
            block_fonts=True,
            block_media=True,
            block_analytics=True,
            viewport_width=1280,
            viewport_height=720,
            disable_gpu=True,
        )

    @classmethod
    def ultra_aggressive(cls) -> "PerformanceSettings":
        """
        Ultra-aggressive preset: Maximum speed, high block risk.
        Only use if you have very good residential IPs.
        """
        return cls(
            fixed_browser_count=5,
            click_delay_min=0.02,
            click_delay_max=0.1,
            nav_delay_min=0.8,
            nav_delay_max=1.5,
            prenav_delay_min=0.5,
            prenav_delay_max=1.2,
            prescrape_delay_min=0.5,
            prescrape_delay_max=1.0,
            networkidle_timeout_ms=2500,
            hydration_max_scrolls=4,
            inter_lease_delay_min=0.5,
            inter_lease_delay_max=1.5,
            warmup_delay_min=1.5,
            warmup_delay_max=2.5,
            store_delay_min=1.0,
            store_delay_max=1.5,
            block_images=True,
            block_fonts=True,
            block_media=True,
            block_analytics=True,
            abort_images_after_dom=True,
            viewport_width=1280,
            viewport_height=720,
            disable_gpu=True,
            pages_per_browser=6,
            slot_stagger_seconds=3,
        )

    def save(self) -> None:
        """Persist settings to disk atomically.

        load() can trigger a save() during the one-time migration, and load()
        runs in the GUI, supervisor, and every slot process — so concurrent
        writers are possible on first post-upgrade launch. Write to a
        pid-unique temp file then os.replace() (atomic rename) so a reader never
        sees a half-written file. Concurrent writers each emit identical
        migrated content, so last-writer-wins is harmless.
        """
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        try:
            tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
            os.replace(tmp, path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            raise

    @classmethod
    def load(cls) -> "PerformanceSettings":
        """Load settings from disk, or return defaults if not found.

        One-time migration: a config saved before the performance optimization
        (no ``settings_version``, or < SETTINGS_VERSION) pinned image/font
        blocking OFF — the single biggest, Akamai-safe speed lever. Such users
        would otherwise silently miss most of the speedup. On first load we turn
        those two flags on (documented safe; the old default was simply off) and
        stamp the new version, WITHOUT touching the detection-sensitive timing
        values the user may have deliberately tuned (e.g. via Conservative).
        """
        path = _settings_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Filter out unknown keys for forward compatibility
            known_keys = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_keys}
            inst = cls(**filtered)

            saved_version = int(data.get("settings_version", 1) or 1)
            if saved_version < SETTINGS_VERSION:
                # Enable the Akamai-safe blocking lever for legacy configs.
                inst.block_images = True
                inst.block_fonts = True
                # Apply the lighter resource profile (smaller viewport, one more
                # window, lean flags) ONLY where the user kept the old defaults —
                # never override an intentional, machine-specific choice.
                if inst.viewport_width == 1440 and inst.viewport_height == 900:
                    inst.viewport_width, inst.viewport_height = 1280, 720
                if inst.max_browsers == 5:
                    inst.max_browsers = 6
                # lean_browser_flags is a new key absent from legacy files, so it
                # already defaults to True for these users.
                inst.settings_version = SETTINGS_VERSION
                try:
                    inst.save()
                except Exception:
                    pass
            return inst
        except Exception:
            return cls()

    def to_env_overrides(self) -> dict[str, str]:
        """
        Convert settings to environment variable overrides.

        These are exported into each slot worker's environment (see slot_worker
        `_run_slot`) so the embedded PARALLEL scraper — which reads env with
        hardcoded fallbacks and never imports this module — actually honors the
        configured pacing. Every tunable knob the scraper reads must appear here,
        otherwise it silently falls back to the scraper's own defaults.
        """
        return {
            "GLOORBOT_FIXED_BROWSER_COUNT": str(self.fixed_browser_count),
            "GLOORBOT_MAX_BROWSERS": str(self.max_browsers),
            "GLOORBOT_CLICK_DELAY_MIN": str(self.click_delay_min),
            "GLOORBOT_CLICK_DELAY_MAX": str(self.click_delay_max),
            "GLOORBOT_NAV_DELAY_MIN": str(self.nav_delay_min),
            "GLOORBOT_NAV_DELAY_MAX": str(self.nav_delay_max),
            "GLOORBOT_PRENAV_DELAY_MIN": str(self.prenav_delay_min),
            "GLOORBOT_PRENAV_DELAY_MAX": str(self.prenav_delay_max),
            "GLOORBOT_PRESCRAPE_DELAY_MIN": str(self.prescrape_delay_min),
            "GLOORBOT_PRESCRAPE_DELAY_MAX": str(self.prescrape_delay_max),
            "GLOORBOT_NETWORKIDLE_TIMEOUT_MS": str(self.networkidle_timeout_ms),
            "GLOORBOT_HYDRATION_MAX_SCROLLS": str(self.hydration_max_scrolls),
            "GLOORBOT_HYDRATION_EARLY_EXIT": "1" if self.hydration_early_exit else "0",
            "GLOORBOT_BLOCK_IMAGES": "1" if self.block_images else "0",
            "GLOORBOT_BLOCK_FONTS": "1" if self.block_fonts else "0",
            "GLOORBOT_BLOCK_MEDIA": "1" if self.block_media else "0",
            "GLOORBOT_BLOCK_ANALYTICS": "1" if self.block_analytics else "0",
            "GLOORBOT_VIEWPORT_WIDTH": str(self.viewport_width),
            "GLOORBOT_VIEWPORT_HEIGHT": str(self.viewport_height),
        }


# Global instance for easy access
_current_settings: PerformanceSettings | None = None


def get_settings() -> PerformanceSettings:
    """Get the current performance settings (lazy load from disk)."""
    global _current_settings
    if _current_settings is None:
        _current_settings = PerformanceSettings.load()
    return _current_settings


def set_settings(settings: PerformanceSettings) -> None:
    """Update the current settings and persist to disk."""
    global _current_settings
    _current_settings = settings
    settings.save()


def reset_settings() -> PerformanceSettings:
    """Reset settings to defaults."""
    global _current_settings
    _current_settings = PerformanceSettings()
    _current_settings.save()
    return _current_settings
