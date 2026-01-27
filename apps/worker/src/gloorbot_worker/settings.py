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

    # Maximum browsers when using dynamic scaling
    max_browsers: int = 5

    # Minimum browsers (always keep at least this many running)
    min_browsers: int = 1

    # === TIMING SETTINGS (in seconds) ===
    # Click delay range: random delay before clicking elements
    # Lower = faster but higher risk of detection
    click_delay_min: float = 0.1
    click_delay_max: float = 0.4

    # Page navigation delay range: delay after loading a page
    # CRITICAL: Too fast triggers Akamai's "inhuman speed" detection
    nav_delay_min: float = 1.5
    nav_delay_max: float = 3.9

    # Inter-lease delay: delay between finishing one task and starting next
    # Matches PARALLEL's pacing to avoid detection
    inter_lease_delay_min: float = 2.0
    inter_lease_delay_max: float = 4.55

    # Warmup duration: time spent on homepage building trust
    warmup_delay_min: float = 3.5
    warmup_delay_max: float = 5.5

    # Store context delay: time after setting store
    store_delay_min: float = 2.0
    store_delay_max: float = 3.0

    # === RESOURCE BLOCKING ===
    # Block images: saves ~60-70% bandwidth, DOM still renders
    # Images are fetched but not decoded/rendered
    block_images: bool = False

    # Block fonts: saves ~5-10% bandwidth, minor visual difference
    block_fonts: bool = False

    # Block media (audio/video): safe to block, rarely used on Lowe's
    block_media: bool = True

    # Block analytics/tracking (except Akamai): saves bandwidth + faster
    # NEVER blocks /_sec/ which is Akamai's bot detection
    block_analytics: bool = True

    # Abort image loading after DOM renders (hybrid approach)
    # Fetches enough to satisfy Akamai but doesn't fully render
    abort_images_after_dom: bool = False

    # === VIEWPORT SETTINGS ===
    # Smaller viewport = faster rendering, less memory
    # Default 1440x900, can reduce to 1280x720 for 37% fewer pixels
    viewport_width: int = 1440
    viewport_height: int = 900

    # === BROWSER LAUNCH ARGS ===
    # These are safe optimizations that don't trigger detection
    disable_gpu: bool = False  # True = faster on low-end machines
    disable_dev_shm: bool = True  # Prevents /dev/shm crashes in containers
    disable_background_networking: bool = True  # Prevents idle traffic
    disable_background_timer_throttling: bool = True
    disable_backgrounding_occluded_windows: bool = True
    disable_renderer_backgrounding: bool = True
    memory_pressure_off: bool = True  # Prevents OOM crashes

    # === CONCURRENT PAGES PER BROWSER ===
    # More pages = faster but higher memory and detection risk
    # PARALLEL uses 4, which is proven safe
    pages_per_browser: int = 4

    # === STAGGER SETTINGS ===
    # Delay between launching slots to prevent concurrent fresh sessions
    slot_stagger_seconds: int = 5

    # === PRESETS ===
    @classmethod
    def conservative(cls) -> "PerformanceSettings":
        """
        Conservative preset: Prioritizes avoiding blocks over speed.
        Use this if you're getting blocked frequently.
        """
        return cls(
            fixed_browser_count=3,
            click_delay_min=0.2,
            click_delay_max=0.6,
            nav_delay_min=2.0,
            nav_delay_max=4.5,
            inter_lease_delay_min=3.0,
            inter_lease_delay_max=6.0,
            block_images=False,
            block_fonts=False,
            viewport_width=1440,
            viewport_height=900,
        )

    @classmethod
    def balanced(cls) -> "PerformanceSettings":
        """
        Balanced preset: Default settings that work reliably.
        Proven in production without triggering blocks.
        """
        return cls()  # Defaults are balanced

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
        """Persist settings to disk."""
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "PerformanceSettings":
        """Load settings from disk, or return defaults if not found."""
        path = _settings_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Filter out unknown keys for forward compatibility
            known_keys = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_keys}
            return cls(**filtered)
        except Exception:
            return cls()

    def to_env_overrides(self) -> dict[str, str]:
        """
        Convert settings to environment variable overrides.
        Useful for passing settings to slot workers.
        """
        return {
            "GLOORBOT_FIXED_BROWSER_COUNT": str(self.fixed_browser_count),
            "GLOORBOT_MAX_BROWSERS": str(self.max_browsers),
            "GLOORBOT_CLICK_DELAY_MIN": str(self.click_delay_min),
            "GLOORBOT_CLICK_DELAY_MAX": str(self.click_delay_max),
            "GLOORBOT_NAV_DELAY_MIN": str(self.nav_delay_min),
            "GLOORBOT_NAV_DELAY_MAX": str(self.nav_delay_max),
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
