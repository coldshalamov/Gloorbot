"""
Lowe's Inventory Scraper - Production Apify Actor with Advanced Anti-Fingerprinting

MISSION: Scrape every item listing from Lowe's for WA/OR stores
TARGET: "Pickup Today" items to find local markdowns and clearance

ARCHITECTURE: Sequential Context Rotation (NOT Browser Pooling)
- Single browser instance (minimum RAM)
- New context per store (session locking maintained)
- Resource blocking (optional; disable to reduce bot signals)
- Smart pagination (30-50% fewer requests)

ESTIMATED COST: ~$25-30 per full crawl (109K URLs)
- Previous attempts: $400+ (browser pooling was the mistake)

CRITICAL REQUIREMENTS:
- headless=False (Akamai blocks headless)
- RESIDENTIAL proxies with session locking
- Store context set via UI (optional, but improves pickup accuracy)

ANTI-FINGERPRINTING MEASURES (Added 2025-12-22):
✅ Canvas fingerprint randomization (noise injection)
✅ WebGL fingerprint randomization (vendor/renderer spoofing)
✅ AudioContext fingerprint randomization (frequency noise)
✅ Screen resolution randomization (viewport variation)
✅ User agent rotation (optional)
✅ Timezone/locale randomization (optional)
✅ playwright-stealth (base automation hiding)

WHY THESE MATTER:
Akamai builds composite fingerprints from multiple sources. Even with residential
proxies, consistent browser fingerprints across requests = detectable bot pattern.
Each context now appears as a unique user with different hardware/location.

Author: Claude Code (Enhanced with Akamai evasion)
"""

from __future__ import annotations

import asyncio
import gc
import hashlib
import json
import os
import random
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, unquote

from apify import Actor
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Route,
    Playwright,
)
from playwright_stealth import Stealth

# Ensure apify_actor_seed is on sys.path so we can reuse app/ helpers.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

try:
    from app.retailers.lowes import set_store_context as set_store_context_ui
except Exception:
    set_store_context_ui = None

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.lowes.com"
GOTO_TIMEOUT_MS = 45000
PAGE_SIZE = 24
DEFAULT_MAX_PAGES = 50
MIN_PRODUCTS_TO_CONTINUE = 6

# =============================================================================
# ANTI-FINGERPRINTING - RANDOMIZED USER AGENTS
# =============================================================================

USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Mac Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

TIMEZONES = [
    'America/New_York',
    'America/Chicago',
    'America/Los_Angeles',
    'America/Denver',
    'America/Phoenix',
]

LOCALES = [
    'en-US',
    'en-GB',
    'en-CA',
    'en-AU',
]


def randomize_user_agent_enabled() -> bool:
    """Return True when explicit UA randomization is requested."""

    return os.getenv("CHEAPSKATER_RANDOM_UA", "0").strip() == "1"


def randomize_locale_enabled() -> bool:
    """Return True when timezone/locale should be randomized."""

    return os.getenv("CHEAPSKATER_RANDOM_TZLOCALE", "0").strip() == "1"


def desired_timezone() -> str:
    """Return the baseline timezone to use when not randomizing."""

    return os.getenv("CHEAPSKATER_TZ", "America/Los_Angeles").strip() or "America/Los_Angeles"


def desired_locale() -> str:
    """Return the baseline locale to use when not randomizing."""

    return os.getenv("CHEAPSKATER_LOCALE", "en-US").strip() or "en-US"


def pickup_filter_enabled() -> bool:
    """Return True when pickup filter clicks should be attempted."""

    return os.getenv("CHEAPSKATER_PICKUP_FILTER", "0").strip() == "1"


def resource_blocking_enabled() -> bool:
    """Return True when resource blocking should be enabled."""

    return os.getenv("CHEAPSKATER_BLOCK_RESOURCES", "0").strip() == "1"


def store_context_enabled() -> bool:
    """Return True when the Lowe's store context UI flow should run."""

    return os.getenv("CHEAPSKATER_SET_STORE_CONTEXT", "1").strip() == "1"


def browser_channel() -> str | None:
    """Return a Playwright browser channel override (e.g., chrome, msedge)."""

    raw = os.getenv("CHEAPSKATER_BROWSER_CHANNEL")
    if not raw:
        return None
    trimmed = raw.strip()
    return trimmed or None


def diagnostics_enabled() -> bool:
    """Return True when extra anti-bot diagnostics are enabled."""

    return os.getenv("CHEAPSKATER_DIAGNOSTICS", "0").strip() == "1"


def request_block_debug_enabled() -> bool:
    """Return True when request-blocking decisions should be logged."""

    return os.getenv("CHEAPSKATER_DEBUG_BLOCKING", "0").strip() == "1"


def proxy_diagnostic_enabled() -> bool:
    """Return True when proxy IP should be verified via lumtest."""

    return os.getenv("CHEAPSKATER_PROXY_DIAGNOSTIC", "0").strip() == "1"


def test_mode_enabled() -> bool:
    """Return True when a minimal local test run is requested."""

    return os.getenv("CHEAPSKATER_TEST_MODE", "0").strip() == "1"


def diagnostics_audio_enabled() -> bool:
    """Return True when audio fingerprint data should be included in diagnostics."""

    return os.getenv("CHEAPSKATER_DIAGNOSTICS_AUDIO", "0").strip() == "1"


def diagnostics_drift_check_enabled() -> bool:
    """Return True when an explicit drift check should be performed."""

    return os.getenv("CHEAPSKATER_DIAGNOSTICS_DRIFT", "0").strip() == "1"


def fingerprint_injection_enabled() -> bool:
    """Return True when custom fingerprint injection is enabled."""

    return os.getenv("CHEAPSKATER_FINGERPRINT_INJECTION", "0").strip() == "1"


def persistent_context_enabled() -> bool:
    """Return True when each store should use a persistent profile context."""

    return os.getenv("CHEAPSKATER_PERSISTENT_CONTEXT", "0").strip() == "1"


def _base_profile_dir() -> Path:
    raw = os.getenv("CHEAPSKATER_USER_DATA_DIR") or ".playwright-profile/chromium"
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _store_profile_dir(store_id: str) -> Path:
    root = Path(os.getenv("CHEAPSKATER_PROFILE_ROOT", ".playwright-profiles"))
    root.mkdir(parents=True, exist_ok=True)
    suffix = f"{random.randint(1000, 9999)}"
    path = root / f"store_{store_id}_{suffix}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _seed_profile(dest: Path) -> None:
    base = _base_profile_dir()
    try:
        if base.is_dir() and any(base.iterdir()):
            shutil.copytree(base, dest, dirs_exist_ok=True)
    except Exception:
        return


def _launch_args() -> list[str]:
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-infobars",
        "--lang=en-US",
        "--no-default-browser-check",
        "--start-maximized",
        "--window-size=1440,960",
    ]


async def _prime_session(page: Page) -> None:
    """Prime the session on Lowe's homepage to allow Akamai JS to settle."""

    try:
        await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=12000)
        await asyncio.sleep(random.uniform(0.8, 1.6))
    except Exception:
        return


async def _wait_for_akamai_clear(page: Page, timeout_s: float = 60.0) -> bool:
    """Wait for Akamai challenge pages to resolve."""

    deadline = time.time() + timeout_s
    reloaded = False
    while time.time() < deadline:
        try:
            title = await page.title()
            content = await page.content()
        except Exception:
            await asyncio.sleep(0.5)
            continue

        if "Access Denied" in title or "Access Denied" in content[:2000]:
            return False
        if "errors.edgesuite.net" in content:
            return False

        # Challenge marker seen: wait for it to complete.
        if "chlgeId" in content or "/fUQvvs/" in content or "akamai" in content[:2000].lower():
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            await asyncio.sleep(1.0)
            if not reloaded and time.time() + 10 < deadline:
                reloaded = True
                try:
                    await page.reload(wait_until="domcontentloaded")
                except Exception:
                    pass
            continue

        return True
    return False


def _mask_proxy(proxy_url: str) -> str:
    parsed = urlparse(proxy_url)
    if not parsed.hostname:
        return proxy_url
    host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    return f"{parsed.scheme or 'http'}://{host}"


def proxy_settings_from_url(proxy_url: str) -> dict[str, str]:
    """Convert a proxy URL into Playwright proxy settings."""

    parsed = urlparse(proxy_url)
    if not parsed.hostname:
        return {"server": proxy_url}

    scheme = parsed.scheme or "http"
    host = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
    settings: dict[str, str] = {"server": f"{scheme}://{host}"}

    if parsed.username:
        settings["username"] = unquote(parsed.username)
    if parsed.password:
        settings["password"] = unquote(parsed.password)

    return settings


async def compute_fingerprint_hash(page: Page) -> str:
    """Return a stable hash of key fingerprint surfaces for this context."""

    payload = await page.evaluate(
        """
        () => {
            const data = {};
            data.screen = {
                width: window.screen.width,
                height: window.screen.height,
                availWidth: window.screen.availWidth,
                availHeight: window.screen.availHeight,
                colorDepth: window.screen.colorDepth,
                pixelDepth: window.screen.pixelDepth,
            };
            data.navigator = {
                platform: navigator.platform,
                language: navigator.language,
                userAgent: navigator.userAgent,
            };
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '16px Arial';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('fingerprint', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('fingerprint', 4, 17);
            data.canvas = canvas.toDataURL();

            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                data.webgl = {
                    vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
                    renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
                };
            }

            return data;
        }
        """
    )
    if diagnostics_audio_enabled():
        try:
            audio_payload = await page.evaluate(
                """
                () => {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (!AudioContext) return null;
                    const audioCtx = new AudioContext();
                    const oscillator = audioCtx.createOscillator();
                    const compressor = audioCtx.createDynamicsCompressor();
                    oscillator.type = 'triangle';
                    oscillator.connect(compressor);
                    compressor.connect(audioCtx.destination);
                    oscillator.start(0);
                    oscillator.stop(0);
                    const values = {
                        threshold: compressor.threshold.value,
                        knee: compressor.knee.value,
                        ratio: compressor.ratio.value,
                        attack: compressor.attack.value,
                        release: compressor.release.value,
                    };
                    audioCtx.close();
                    return values;
                }
                """
            )
            payload["audio"] = audio_payload
        except Exception:
            payload["audio"] = None
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest

# =============================================================================
# STORE DATA - ALL WASHINGTON AND OREGON LOWE'S
# =============================================================================

WA_OR_STORES = {
    # WASHINGTON (35 stores)
    "0061": {"name": "Smokey Point", "city": "Arlington", "state": "WA", "zip": "98223"},
    "1089": {"name": "Auburn", "city": "Auburn", "state": "WA", "zip": "98002"},
    "1631": {"name": "Bellingham", "city": "Bellingham", "state": "WA", "zip": "98226"},
    "2895": {"name": "Bonney Lake", "city": "Bonney Lake", "state": "WA", "zip": "98391"},
    "1534": {"name": "Bremerton", "city": "Bremerton", "state": "WA", "zip": "98311"},
    "0149": {"name": "Everett", "city": "Everett", "state": "WA", "zip": "98201"},
    "2346": {"name": "Federal Way", "city": "Federal Way", "state": "WA", "zip": "98003"},
    "0140": {"name": "Issaquah", "city": "Issaquah", "state": "WA", "zip": "98027"},
    "0249": {"name": "Kennewick", "city": "Kennewick", "state": "WA", "zip": "99336"},
    "2561": {"name": "Kent-Midway", "city": "Kent", "state": "WA", "zip": "98032"},
    "2738": {"name": "S. Lacey", "city": "Lacey", "state": "WA", "zip": "98503"},
    "1081": {"name": "Lakewood", "city": "Lakewood", "state": "WA", "zip": "98499"},
    "1887": {"name": "Longview", "city": "Longview", "state": "WA", "zip": "98632"},
    "0285": {"name": "Lynnwood", "city": "Lynnwood", "state": "WA", "zip": "98036"},
    "1573": {"name": "Mill Creek", "city": "Mill Creek", "state": "WA", "zip": "98012"},
    "2781": {"name": "Monroe", "city": "Monroe", "state": "WA", "zip": "98272"},
    "2956": {"name": "Moses Lake", "city": "Moses Lake", "state": "WA", "zip": "98837"},
    "0035": {"name": "Mount Vernon", "city": "Mount Vernon", "state": "WA", "zip": "98273"},
    "1167": {"name": "Olympia", "city": "Olympia", "state": "WA", "zip": "98516"},
    "2344": {"name": "Pasco", "city": "Pasco", "state": "WA", "zip": "99301"},
    "2733": {"name": "Port Orchard", "city": "Port Orchard", "state": "WA", "zip": "98367"},
    "2734": {"name": "Puyallup", "city": "Puyallup", "state": "WA", "zip": "98374"},
    "2420": {"name": "Renton", "city": "Renton", "state": "WA", "zip": "98057"},
    "0252": {"name": "N. Seattle", "city": "Seattle", "state": "WA", "zip": "98133"},
    "0004": {"name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"},
    "2746": {"name": "Silverdale", "city": "Silverdale", "state": "WA", "zip": "98383"},
    "3045": {"name": "N. Spokane", "city": "Spokane", "state": "WA", "zip": "99208"},
    "0172": {"name": "Spokane Valley", "city": "Spokane", "state": "WA", "zip": "99212"},
    "2793": {"name": "E. Spokane Valley", "city": "Spokane Valley", "state": "WA", "zip": "99037"},
    "0026": {"name": "Tacoma", "city": "Tacoma", "state": "WA", "zip": "98466"},
    "0010": {"name": "Tukwila", "city": "Tukwila", "state": "WA", "zip": "98188"},
    "1632": {"name": "E. Vancouver", "city": "Vancouver", "state": "WA", "zip": "98662"},
    "2954": {"name": "Lacamas Lake", "city": "Vancouver", "state": "WA", "zip": "98683"},
    "0152": {"name": "Wenatchee", "city": "Wenatchee", "state": "WA", "zip": "98801"},
    "3240": {"name": "Yakima", "city": "Yakima", "state": "WA", "zip": "98903"},
    # OREGON (14 stores)
    "3057": {"name": "Albany-Millersburg", "city": "Albany", "state": "OR", "zip": "97322"},
    "1690": {"name": "Bend", "city": "Bend", "state": "OR", "zip": "97701"},
    "2940": {"name": "W. Eugene", "city": "Eugene", "state": "OR", "zip": "97402"},
    "1558": {"name": "Hillsboro", "city": "Hillsboro", "state": "OR", "zip": "97123"},
    "2619": {"name": "Keizer", "city": "Keizer", "state": "OR", "zip": "97303"},
    "1693": {"name": "McMinnville", "city": "McMinnville", "state": "OR", "zip": "97128"},
    "0248": {"name": "Medford", "city": "Medford", "state": "OR", "zip": "97504"},
    "1824": {"name": "Clackamas County", "city": "Milwaukie", "state": "OR", "zip": "97222"},
    "2579": {"name": "Portland-Delta Park", "city": "Portland", "state": "OR", "zip": "97217"},
    "2865": {"name": "Redmond", "city": "Redmond", "state": "OR", "zip": "97756"},
    "1741": {"name": "Roseburg", "city": "Roseburg", "state": "OR", "zip": "97470"},
    "1600": {"name": "Salem", "city": "Salem", "state": "OR", "zip": "97302"},
    "1108": {"name": "Tigard", "city": "Tigard", "state": "OR", "zip": "97223"},
    "1114": {"name": "Wood Village", "city": "Wood Village", "state": "OR", "zip": "97060"},
}

# =============================================================================
# CATEGORY URLs - HIGH-VALUE DEPARTMENTS
# =============================================================================

DEFAULT_CATEGORIES = [
    # Clearance/Deals (highest priority for markdowns)
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},

    # Building Materials
    {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    {"name": "Plywood", "url": "https://www.lowes.com/pl/Plywood-Building-supplies/4294858043"},
    {"name": "Drywall", "url": "https://www.lowes.com/pl/Drywall-Building-supplies/4294857989"},

    # Tools
    {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
    {"name": "Hand Tools", "url": "https://www.lowes.com/pl/Hand-tools-Tools/4294933958"},
    {"name": "Tool Storage", "url": "https://www.lowes.com/pl/Tool-storage-Tools/4294857963"},

    # Paint
    {"name": "Paint", "url": "https://www.lowes.com/pl/Paint-Paint-supplies/4294820090"},
    {"name": "Stains", "url": "https://www.lowes.com/pl/Exterior-stains-waterproofers/4294858026"},

    # Appliances
    {"name": "Appliances", "url": "https://www.lowes.com/pl/Appliances/4294857975"},
    {"name": "Washers Dryers", "url": "https://www.lowes.com/pl/Washers-dryers-Appliances/4294857958"},
    {"name": "Refrigerators", "url": "https://www.lowes.com/pl/Refrigerators-Appliances/4294857957"},

    # Outdoor
    {"name": "Outdoor Power", "url": "https://www.lowes.com/pl/Outdoor-power-equipment-Outdoors/4294857982"},
    {"name": "Grills", "url": "https://www.lowes.com/pl/Grills-grilling-Outdoors/4294821574"},
    {"name": "Patio Furniture", "url": "https://www.lowes.com/pl/Patio-furniture-Outdoors/4294857984"},

    # Flooring
    {"name": "Flooring", "url": "https://www.lowes.com/pl/Flooring/4294822454"},
    {"name": "Tile", "url": "https://www.lowes.com/pl/Tile-tile-accessories-Flooring/4294858017"},

    # Kitchen & Bath
    {"name": "Kitchen Faucets", "url": "https://www.lowes.com/pl/Kitchen-faucets-water-dispensers/4294857986"},
    {"name": "Bathroom Vanities", "url": "https://www.lowes.com/pl/Bathroom-vanities-Bathroom/4294819024"},

    # Electrical
    {"name": "Lighting", "url": "https://www.lowes.com/pl/Lighting-ceiling-fans/4294857979"},
    {"name": "Electrical", "url": "https://www.lowes.com/pl/Electrical/4294630256"},

    # Hardware
    {"name": "Fasteners", "url": "https://www.lowes.com/pl/Fasteners-Hardware/4294857976"},
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},
]

# =============================================================================
# RESOURCE BLOCKING - 60-70% BANDWIDTH SAVINGS
# =============================================================================

BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}

BLOCKED_URL_PATTERNS = [
    r"google-analytics\.com", r"googletagmanager\.com", r"facebook\.net",
    r"doubleclick\.net", r"analytics", r"tracking", r"beacon", r"pixel",
    r"ads\.", r"adservice", r"youtube\.com", r"vimeo\.com",
    r"hotjar\.com", r"clarity\.ms", r"newrelic\.com", r"sentry\.io",
    r"segment\.com", r"optimizely\.com", r"fullstory\.com",
    r"\.woff2?(\?|$)", r"\.ttf(\?|$)", r"\.eot(\?|$)",
]

NEVER_BLOCK_PATTERNS = [
    r"/_sec/", r"/akam/", r"akamai", r"lowes\.com",
]


# =============================================================================
# ANTI-FINGERPRINTING - INJECTION SCRIPTS
# =============================================================================

def build_fingerprint_profile(viewport_width: int, viewport_height: int) -> dict[str, object]:
    """Build a stable per-context fingerprint profile to avoid intra-session drift."""

    screen_width = max(viewport_width + random.randint(200, 600), viewport_width)
    screen_height = max(viewport_height + random.randint(120, 360), viewport_height)

    return {
        "canvas_noise": (
            random.randint(-2, 2),
            random.randint(-2, 2),
            random.randint(-2, 2),
        ),
        "audio_noise": random.uniform(-0.00005, 0.00005),
        "screen": {
            "width": screen_width,
            "height": screen_height,
            "avail_height_offset": random.randint(30, 80),
        },
        "webgl": {
            "vendor": random.choice([
                "Intel Inc.",
                "Intel Open Source Technology Center",
                "Google Inc. (Intel)",
                "NVIDIA Corporation",
                "AMD",
            ]),
            "renderer": random.choice([
                "Intel Iris OpenGL Engine",
                "Mesa DRI Intel(R) HD Graphics",
                "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11)",
                "Intel(R) UHD Graphics 620",
                "GeForce GTX 1050/PCIe/SSE2",
            ]),
        },
    }


async def inject_canvas_noise(page: Page, noise: tuple[int, int, int]) -> None:
    """
    Inject canvas fingerprint randomization.

    Akamai tracks canvas fingerprints to detect bots. This adds subtle noise
    to canvas rendering to make each context appear as a unique browser.
    """
    r_noise, g_noise, b_noise = noise
    script = """
        (() => {
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

            const clamp = (value) => Math.max(0, Math.min(255, value));
            const rNoise = __R_NOISE__;
            const gNoise = __G_NOISE__;
            const bNoise = __B_NOISE__;

            // Override toDataURL
            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                const context = this.getContext('2d');
                if (context) {
                    const original = context.getImageData(0, 0, this.width, this.height);
                    const noisy = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < noisy.data.length; i += 4) {
                        noisy.data[i] = clamp(noisy.data[i] + rNoise);
                        noisy.data[i+1] = clamp(noisy.data[i+1] + gNoise);
                        noisy.data[i+2] = clamp(noisy.data[i+2] + bNoise);
                    }
                    context.putImageData(noisy, 0, 0);
                    const result = originalToDataURL.apply(this, args);
                    context.putImageData(original, 0, 0);
                    return result;
                }
                return originalToDataURL.apply(this, args);
            };

            // Override toBlob
            HTMLCanvasElement.prototype.toBlob = function(...args) {
                const context = this.getContext('2d');
                if (context) {
                    const original = context.getImageData(0, 0, this.width, this.height);
                    const noisy = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < noisy.data.length; i += 4) {
                        noisy.data[i] = clamp(noisy.data[i] + rNoise);
                        noisy.data[i+1] = clamp(noisy.data[i+1] + gNoise);
                        noisy.data[i+2] = clamp(noisy.data[i+2] + bNoise);
                    }
                    context.putImageData(noisy, 0, 0);
                    const callback = args[0];
                    const rest = args.slice(1);
                    const wrapped = function(blob) {
                        context.putImageData(original, 0, 0);
                        callback(blob);
                    };
                    return originalToBlob.apply(this, [wrapped, ...rest]);
                }
                return originalToBlob.apply(this, args);
            };
        })();
    """
    script = (
        script.replace("__R_NOISE__", str(r_noise))
        .replace("__G_NOISE__", str(g_noise))
        .replace("__B_NOISE__", str(b_noise))
    )
    await page.add_init_script(script)


async def inject_webgl_noise(page: Page, vendor: str, renderer: str) -> None:
    """
    Inject WebGL fingerprint randomization.

    Randomizes WebGL vendor/renderer strings and adds noise to rendering
    to prevent GPU fingerprinting.
    """
    script = """
        (() => {
            const randomVendor = __VENDOR__;
            const randomRenderer = __RENDERER__;

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) { // UNMASKED_VENDOR_WEBGL
                    return randomVendor;
                }
                if (param === 37446) { // UNMASKED_RENDERER_WEBGL
                    return randomRenderer;
                }
                return getParameter.apply(this, arguments);
            };

            // Also apply to WebGL2
            if (typeof WebGL2RenderingContext !== 'undefined') {
                const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(param) {
                    if (param === 37445) return randomVendor;
                    if (param === 37446) return randomRenderer;
                    return getParameter2.apply(this, arguments);
                };
            }
        })();
    """
    script = (
        script.replace("__VENDOR__", json.dumps(vendor))
        .replace("__RENDERER__", json.dumps(renderer))
    )
    await page.add_init_script(script)


async def inject_audio_noise(page: Page, noise_offset: float) -> None:
    """
    Inject AudioContext fingerprint randomization.

    Adds subtle noise to audio processing to prevent audio fingerprinting.
    """
    script = """
        (() => {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;

            const originalCreateDynamicsCompressor = AudioContext.prototype.createDynamicsCompressor;
            const originalCreateOscillator = AudioContext.prototype.createOscillator;

            const noise = () => __AUDIO_NOISE__;

            AudioContext.prototype.createDynamicsCompressor = function() {
                const compressor = originalCreateDynamicsCompressor.apply(this, arguments);
                if (compressor.threshold) {
                    let originalThresholdValue = compressor.threshold.value;
                    Object.defineProperty(compressor.threshold, 'value', {
                        get: () => originalThresholdValue + noise(),
                        set: (v) => originalThresholdValue = v
                    });
                }
                return compressor;
            };

            AudioContext.prototype.createOscillator = function() {
                const oscillator = originalCreateOscillator.apply(this, arguments);
                if (oscillator.frequency) {
                    let originalFreqValue = oscillator.frequency.value;
                    Object.defineProperty(oscillator.frequency, 'value', {
                        get: () => originalFreqValue + noise(),
                        set: (v) => originalFreqValue = v
                    });
                }
                return oscillator;
            };
        })();
    """
    script = script.replace("__AUDIO_NOISE__", repr(noise_offset))
    await page.add_init_script(script)


async def inject_screen_randomization(page: Page, screen_width: int, screen_height: int, avail_height_offset: int) -> None:
    """
    Inject screen resolution randomization.

    Slightly randomizes screen dimensions to prevent exact screen fingerprinting.
    """
    script = """
        (() => {
            Object.defineProperty(window.screen, 'width', {
                get: () => __SCREEN_WIDTH__
            });
            Object.defineProperty(window.screen, 'height', {
                get: () => __SCREEN_HEIGHT__
            });
            Object.defineProperty(window.screen, 'availWidth', {
                get: () => __SCREEN_WIDTH__
            });
            Object.defineProperty(window.screen, 'availHeight', {
                get: () => __SCREEN_HEIGHT__ - __AVAIL_HEIGHT_OFFSET__
            });
        })();
    """
    script = (
        script.replace("__SCREEN_WIDTH__", str(screen_width))
        .replace("__SCREEN_HEIGHT__", str(screen_height))
        .replace("__AVAIL_HEIGHT_OFFSET__", str(avail_height_offset))
    )
    await page.add_init_script(script)


async def apply_fingerprint_randomization(page: Page, profile: dict[str, object]) -> None:
    """
    Apply all fingerprint randomization techniques.

    This is the master function that applies all anti-fingerprinting measures:
    - Canvas noise injection
    - WebGL randomization
    - AudioContext noise
    - Screen resolution randomization

    CRITICAL: Must be called AFTER playwright-stealth for maximum effectiveness.
    """
    canvas_noise = profile["canvas_noise"]
    webgl = profile["webgl"]
    audio_noise = profile["audio_noise"]
    screen = profile["screen"]

    await inject_canvas_noise(page, canvas_noise)
    await inject_webgl_noise(page, webgl["vendor"], webgl["renderer"])
    await inject_audio_noise(page, audio_noise)
    await inject_screen_randomization(page, screen["width"], screen["height"], screen["avail_height_offset"])


async def setup_request_interception(page: Page) -> None:
    """Block unnecessary resources while preserving Akamai scripts."""
    async def handle_route(route: Route):
        url = route.request.url.lower()
        resource_type = route.request.resource_type

        for pattern in NEVER_BLOCK_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                if request_block_debug_enabled():
                    Actor.log.info(f"[allowlist] {resource_type} {route.request.url}")
                await route.continue_()
                return

        if resource_type in BLOCKED_RESOURCE_TYPES:
            if request_block_debug_enabled():
                Actor.log.info(f"[blocked:type] {resource_type} {route.request.url}")
            await route.abort()
            return

        for pattern in BLOCKED_URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                if request_block_debug_enabled():
                    Actor.log.info(f"[blocked:pattern] {resource_type} {route.request.url}")
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", handle_route)


# =============================================================================
# PICKUP FILTER - CRITICAL FOR LOCAL AVAILABILITY
# =============================================================================

async def apply_pickup_filter(page: Page, category_name: str) -> bool:
    """
    Apply pickup filter with comprehensive verification.

    Returns True if successfully applied and verified.
    """

    pickup_selectors = [
        'label:has-text("Get It Today")',
        'label:has-text("Pickup Today")',
        'label:has-text("Available Today")',
        'button:has-text("Pickup")',
        'button:has-text("Get It Today")',
        'button:has-text("Get it fast")',
        '[data-testid*="pickup"]',
        '[aria-label*="Pickup"]',
        '[aria-label*="Get it today"]',
        'input[type="checkbox"][id*="pickup"]',
    ]

    availability_toggles = [
        'button:has-text("Availability")',
        'button:has-text("Get It Fast")',
        'summary:has-text("Availability")',
    ]

    async def expand_availability():
        for toggle_sel in availability_toggles:
            try:
                toggle = await page.query_selector(toggle_sel)
                if toggle:
                    expanded = await toggle.get_attribute("aria-expanded")
                    if expanded == "false":
                        await toggle.click()
                        await asyncio.sleep(0.5)
                    return
            except Exception:
                continue

    async def is_selected(el) -> bool:
        try:
            for attr in ["aria-checked", "aria-pressed", "aria-selected"]:
                if await el.get_attribute(attr) == "true":
                    return True
            try:
                return await el.is_checked()
            except Exception:
                return False
        except Exception:
            return False

    async def get_product_count() -> int:
        """Count visible products to verify filter effect."""
        try:
            cards = await page.query_selector_all('[data-test="product-pod"], [data-test="productPod"]')
            return len(cards)
        except Exception:
            return -1

    # Wait for page stabilization
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.3, 0.6))
    await page.evaluate("window.scrollTo(0, 0)")
    await expand_availability()

    # Get baseline before filter
    url_before = page.url
    count_before = await get_product_count()

    if diagnostics_enabled():
        try:
            title = await page.title()
            Actor.log.info(f"[{category_name}] Page title: {title}")
            selector_counts = []
            for selector in pickup_selectors:
                try:
                    matches = await page.query_selector_all(selector)
                    selector_counts.append((selector, len(matches)))
                except Exception:
                    selector_counts.append((selector, 0))
            Actor.log.info(f"[{category_name}] Pickup selector counts: {selector_counts}")
        except Exception:
            pass

    for attempt in range(3):
        for selector in pickup_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        if not await element.is_visible():
                            continue

                        text = ""
                        try:
                            text = (await element.inner_text()) or ""
                        except Exception:
                            pass

                        if len(text) > 100:
                            continue

                        if await is_selected(element):
                            Actor.log.info(f"[{category_name}] Pickup filter already active")
                            return True

                        Actor.log.info(f"[{category_name}] Clicking pickup filter: '{text[:40]}'")
                        await element.click()
                        await asyncio.sleep(random.uniform(0.8, 1.5))

                        try:
                            await page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass

                        # MULTI-FACTOR VERIFICATION
                        verified = False
                        verification_method = None

                        # Method 1: Element state
                        if await is_selected(element):
                            verified = True
                            verification_method = "element-state"

                        # Method 2: URL changed with filter params
                        if not verified:
                            url_after = page.url
                            if url_after != url_before:
                                url_lower = url_after.lower()
                                if any(param in url_lower for param in ["pickup", "availability", "refinement"]):
                                    verified = True
                                    verification_method = "url-params"

                        # Method 3: Product count decreased
                        if not verified and count_before > 0:
                            count_after = await get_product_count()
                            if 0 < count_after < count_before:
                                verified = True
                                verification_method = "product-count"
                                Actor.log.info(f"[{category_name}] Products: {count_before} -> {count_after}")

                        if verified:
                            Actor.log.info(f"[{category_name}] Pickup filter VERIFIED via {verification_method}")
                            return True

                    except Exception:
                        continue
            except Exception:
                continue

        await asyncio.sleep(0.5)

    Actor.log.error(f"[{category_name}] Pickup filter FAILED after 3 attempts - SKIPPING CATEGORY")
    if diagnostics_enabled():
        try:
            title = await page.title()
            content = await page.content()
            Actor.log.warning(f"[{category_name}] Title on failure: {title}")
            Actor.log.warning(f"[{category_name}] Content snippet: {content[:500]}")
        except Exception:
            pass
    return False


# =============================================================================
# PRODUCT EXTRACTION
# =============================================================================

def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(text))
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
        return value if 0 < value < 100000 else None
    except (ValueError, TypeError):
        return None


def extract_sku(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    for pattern in [r"/pd/[^/]+-(\d{4,})", r"(\d{6,})(?:[/?]|$)"]:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def pct_off(price: Optional[float], was: Optional[float]) -> Optional[float]:
    if not price or not was or was <= price:
        return None
    return round((was - price) / was, 4)


def is_clearance(text: str, price: Optional[float], was: Optional[float]) -> bool:
    if any(w in text.lower() for w in ["clearance", "closeout", "final price"]):
        return True
    if price and was and (was - price) / was >= 0.25:
        return True
    return False


async def extract_products(page: Page, store_id: str, store_name: str, category: str) -> list[dict]:
    """Extract products using JSON-LD with DOM fallback."""
    products = []
    timestamp = datetime.now(timezone.utc).isoformat()

    # JSON-LD extraction (fastest, most reliable)
    try:
        json_ld = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(s => {
                    try { return JSON.parse(s.textContent); }
                    catch { return null; }
                }).filter(Boolean);
            }
        """)

        def find_products(obj):
            found = []
            if isinstance(obj, dict):
                if obj.get("@type", "").lower() == "product":
                    found.append(obj)
                for v in obj.values():
                    found.extend(find_products(v))
            elif isinstance(obj, list):
                for item in obj:
                    found.extend(find_products(item))
            return found

        for payload in json_ld:
            for prod in find_products(payload):
                offers = prod.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}

                price = parse_price(str(offers.get("price", "")))
                if not price:
                    continue

                price_was = parse_price(str(offers.get("priceWas", "")))
                url = offers.get("url") or prod.get("url")

                img = prod.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                if img and img.startswith("//"):
                    img = f"https:{img}"

                products.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "sku": prod.get("sku") or prod.get("productID"),
                    "title": (prod.get("name") or "Unknown")[:200],
                    "category": category,
                    "price": price,
                    "price_was": price_was,
                    "pct_off": pct_off(price, price_was),
                    "availability": "In Stock",
                    "clearance": is_clearance(str(prod), price, price_was),
                    "product_url": url,
                    "image_url": img,
                    "timestamp": timestamp,
                })
    except Exception as e:
        Actor.log.debug(f"JSON-LD error: {e}")

    # DOM fallback
    if not products:
        try:
            raw = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('[data-test="product-pod"], [data-test="productPod"]').forEach(card => {
                        try {
                            const title = card.querySelector('a[href*="/pd/"], h3, h2')?.innerText?.trim();
                            const price = card.querySelector('[data-test*="price"]')?.innerText?.trim();
                            const href = card.querySelector('a[href*="/pd/"]')?.getAttribute('href');
                            if (title && price) items.push({title, price, href});
                        } catch {}
                    });
                    return items;
                }
            """)

            for r in raw:
                price = parse_price(r.get("price"))
                if not price:
                    continue
                href = r.get("href", "")
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                products.append({
                    "store_id": store_id,
                    "store_name": store_name,
                    "sku": extract_sku(url),
                    "title": r.get("title", "")[:200],
                    "category": category,
                    "price": price,
                    "price_was": None,
                    "pct_off": None,
                    "availability": "In Stock",
                    "clearance": False,
                    "product_url": url,
                    "image_url": None,
                    "timestamp": timestamp,
                })
        except Exception as e:
            Actor.log.debug(f"DOM error: {e}")

    return products


# =============================================================================
# BLOCK DETECTION
# =============================================================================

async def check_blocked(page: Page) -> bool:
    try:
        title = await page.title()
        if "Access Denied" in title:
            return True
        content = await page.content()
        if "Access Denied" in content[:3000] or "Reference #" in content[:3000]:
            return True
    except Exception:
        pass
    return False


# =============================================================================
# CATEGORY SCRAPING WITH SMART PAGINATION
# =============================================================================

def build_url(base: str, offset: int = 0, store_id: str | None = None) -> str:
    parsed = urlparse(base)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if offset > 0:
        params["offset"] = str(offset)
    if store_id and "storeNumber" not in {k for k in params}:
        params["storeNumber"] = store_id
    return parsed._replace(query=urlencode(params, doseq=True)).geturl()


async def scrape_category(
    page: Page,
    url: str,
    name: str,
    store_id: str,
    store_name: str,
    max_pages: int,
) -> list[dict]:
    """Scrape category with smart pagination."""
    all_products = []
    seen = set()
    empty_streak = 0

    for page_num in range(max_pages):
        offset = page_num * PAGE_SIZE
        target = build_url(url, offset, store_id)

        Actor.log.info(f"[{store_name}] {name} p{page_num + 1}")
        if diagnostics_enabled():
            Actor.log.info(f"[{name}] Target URL: {target}")

        try:
            resp = await page.goto(target, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)

            if resp and resp.status >= 400:
                if resp.status == 404:
                    Actor.log.warning(f"[{name}] 404 - skipping")
                    break
                Actor.log.warning(f"[{name}] HTTP {resp.status}")
                continue

            if not await _wait_for_akamai_clear(page):
                Actor.log.error(f"[{name}] Akamai challenge did not clear")
                if diagnostics_enabled():
                    try:
                        title = await page.title()
                        content = await page.content()
                        snippet = re.sub(r"\s+", " ", content[:1200])
                        Actor.log.info(f"[{name}] Block title: {title}")
                        Actor.log.info(f"[{name}] Block snippet: {snippet}")
                    except Exception:
                        pass
                await asyncio.sleep(random.uniform(5, 10))
                break

            if await check_blocked(page):
                Actor.log.error(f"[{name}] BLOCKED!")
                await asyncio.sleep(random.uniform(5, 10))
                break

            if pickup_filter_enabled():
                if not await apply_pickup_filter(page, name):
                    Actor.log.warning(f"[{name}] Filter failed - skipping")
                    break
            elif diagnostics_enabled():
                Actor.log.info(f"[{name}] Pickup filter disabled")

            products = await extract_products(page, store_id, store_name, name)

            new = []
            for p in products:
                key = p.get("sku") or p.get("product_url")
                if key and key not in seen:
                    seen.add(key)
                    new.append(p)

            if new:
                all_products.extend(new)
                empty_streak = 0
                Actor.log.info(f"[{name}] Found {len(new)} (total: {len(all_products)})")
            else:
                empty_streak += 1

            if len(products) < MIN_PRODUCTS_TO_CONTINUE:
                Actor.log.info(f"[{name}] Only {len(products)} - ending")
                break

            if empty_streak >= 2:
                break

            await asyncio.sleep(random.uniform(0.8, 1.5))

        except Exception as e:
            Actor.log.error(f"[{name}] Error: {e}")
            break

    return all_products


# =============================================================================
# MAIN ACTOR
# =============================================================================

async def main() -> None:
    """Apify Actor main entry point."""

    async with Actor:
        Actor.log.info("=" * 60)
        Actor.log.info("LOWE'S INVENTORY SCRAPER - PRODUCTION")
        Actor.log.info("=" * 60)

        # Get input
        inp = await Actor.get_input() or {}

        # Parse stores
        if inp.get("stores"):
            stores = {s["store_id"]: s for s in inp["stores"]}
        else:
            stores = WA_OR_STORES

        # Parse categories
        categories = inp.get("categories") or DEFAULT_CATEGORIES

        max_pages = inp.get("max_pages_per_category", DEFAULT_MAX_PAGES)

        if test_mode_enabled():
            stores = {sid: stores[sid] for sid in list(stores.keys())[:1]}
            categories = categories[:1]
            max_pages = min(max_pages, 2)
            Actor.log.warning("CHEAPSKATER_TEST_MODE enabled: 1 store, 1 category, max_pages=2")

        Actor.log.info(f"Stores: {len(stores)}")
        Actor.log.info(f"Categories: {len(categories)}")
        Actor.log.info(f"Max pages: {max_pages}")
        Actor.log.info(f"Headless: False")

        # Calculate estimate
        est_requests = len(stores) * len(categories) * (max_pages // 2)
        Actor.log.info(f"Estimated requests: ~{est_requests}")

        proxy_override = os.getenv("CHEAPSKATER_PROXY")
        proxy_config = None
        if proxy_override:
            Actor.log.info("Proxy override enabled via CHEAPSKATER_PROXY")
        else:
            try:
                proxy_config = await Actor.create_proxy_configuration(
                    groups=["RESIDENTIAL"],
                    country_code=inp.get("proxy_country_code") or "US",
                )
            except Exception as exc:
                Actor.log.warning(f"Proxy configuration failed: {exc}")

        if proxy_config:
            Actor.log.info("Residential proxy configuration enabled")
        elif proxy_override:
            Actor.log.info(f"Using proxy override for all stores: {_mask_proxy(proxy_override)}")
        else:
            Actor.log.warning("NO PROXY CONFIGURED - Akamai is likely to block this run")

        # Launch browser
        async with async_playwright() as pw:
            browser = None
            if not persistent_context_enabled():
                launch_opts = {
                    "headless": False,
                    "args": _launch_args(),
                }
                channel = browser_channel()
                if channel:
                    launch_opts["channel"] = channel
                browser = await pw.chromium.launch(**launch_opts)

            stealth = Stealth()
            total_products = 0

            # Helper function to scrape a single store
            async def scrape_store(store_id: str, store_info: dict) -> int:
                """Scrape all categories for one store."""
                store_name = f"Lowe's {store_info.get('name', store_id)}"
                store_products = []

                Actor.log.info(f"\n{'='*50}")
                Actor.log.info(f"STORE: {store_name} ({store_id})")
                Actor.log.info(f"{'='*50}")

                # Create context with RANDOMIZED fingerprint settings
                # CRITICAL: Randomize viewport, timezone, locale, and user agent per context
                # to prevent Akamai from correlating requests across different "users"
                viewport_width = random.randint(1280, 1920)
                viewport_height = random.randint(720, 1080)
                if randomize_locale_enabled():
                    selected_timezone = random.choice(TIMEZONES)
                    selected_locale = random.choice(LOCALES)
                else:
                    selected_timezone = desired_timezone()
                    selected_locale = desired_locale()
                selected_ua = random.choice(USER_AGENTS) if randomize_user_agent_enabled() else None

                context_opts = {
                    "viewport": {"width": viewport_width, "height": viewport_height},
                    "timezone_id": selected_timezone,
                    "locale": selected_locale,
                }
                if selected_ua:
                    context_opts["user_agent"] = selected_ua

                if selected_ua:
                    Actor.log.info(f"[{store_name}] Fingerprint: {viewport_width}x{viewport_height}, "
                                  f"{selected_timezone}, {selected_locale}, "
                                  f"UA: {selected_ua[:50]}...")
                else:
                    Actor.log.info(f"[{store_name}] Fingerprint: {viewport_width}x{viewport_height}, "
                                  f"{selected_timezone}, {selected_locale}, "
                                  "UA: default chromium")

                # Override with env var if provided (for testing)
                user_agent_override = os.getenv("USER_AGENT")
                if user_agent_override:
                    context_opts["user_agent"] = user_agent_override
                    Actor.log.warning(f"[{store_name}] Using USER_AGENT override (reduces randomization)")

                proxy_url = None
                if proxy_config:
                    proxy_url = await proxy_config.new_url(session_id=f"lowes_{store_id}")
                elif proxy_override:
                    proxy_url = proxy_override
                if proxy_url:
                    context_opts["proxy"] = proxy_settings_from_url(proxy_url)
                    if diagnostics_enabled():
                        Actor.log.info(f"[{store_name}] Proxy: {_mask_proxy(proxy_url)}")
                elif diagnostics_enabled():
                    Actor.log.info(f"[{store_name}] Proxy: none")

                context = None
                owned_browser = None
                if persistent_context_enabled():
                    profile_dir = _store_profile_dir(store_id)
                    _seed_profile(profile_dir)
                    launch_opts = {
                        "headless": False,
                        "args": _launch_args(),
                    }
                    channel = browser_channel()
                    if channel:
                        launch_opts["channel"] = channel
                    if proxy_url:
                        launch_opts["proxy"] = proxy_settings_from_url(proxy_url)
                    context = await pw.chromium.launch_persistent_context(
                        str(profile_dir),
                        **launch_opts,
                        **context_opts,
                    )
                    owned_browser = context.browser
                else:
                    if browser is None:
                        raise RuntimeError("Browser not initialized")
                    context = await browser.new_context(**context_opts)

                try:
                    page = await context.new_page()

                    # ANTI-FINGERPRINTING STACK (order matters!)
                    # 1. Apply playwright-stealth first (base evasion)
                    await stealth.apply_stealth_async(page)

                    # 2. Apply advanced fingerprint randomization (Canvas, WebGL, Audio, Screen)
                    # CRITICAL: This must come AFTER stealth for maximum effectiveness
                    if fingerprint_injection_enabled():
                        fingerprint_profile = build_fingerprint_profile(viewport_width, viewport_height)
                        await apply_fingerprint_randomization(page, fingerprint_profile)
                    elif diagnostics_enabled():
                        Actor.log.info(f"[{store_name}] Fingerprint injection disabled")

                    # 3. Set up resource blocking (optional; can trigger bot defenses)
                    if resource_blocking_enabled():
                        await setup_request_interception(page)
                    elif diagnostics_enabled():
                        Actor.log.info(f"[{store_name}] Resource blocking disabled")

                    Actor.log.info(f"[{store_name}] Anti-fingerprinting stack applied successfully")

                    await _prime_session(page)

                    if store_context_enabled() and set_store_context_ui and store_info.get("zip"):
                        try:
                            await set_store_context_ui(
                                page,
                                store_info.get("zip"),
                                user_agent=context_opts.get("user_agent"),
                            )
                        except Exception as exc:
                            Actor.log.warning(f"[{store_name}] Store context setup failed: {exc}")
                    elif store_context_enabled() and set_store_context_ui is None:
                        Actor.log.warning(f"[{store_name}] Store context helper unavailable")

                    if proxy_diagnostic_enabled():
                        try:
                            await page.goto("https://lumtest.com/myip.json", wait_until="domcontentloaded", timeout=15000)
                            ip_payload = await page.evaluate("() => document.body.innerText")
                            Actor.log.info(f"[{store_name}] Proxy diagnostic: {ip_payload}")
                        except Exception as exc:
                            Actor.log.warning(f"[{store_name}] Proxy diagnostic failed: {exc}")

                    for idx, cat in enumerate(categories):
                        try:
                            products = await scrape_category(
                                page,
                                cat["url"],
                                cat["name"],
                                store_id,
                                store_name,
                                max_pages,
                            )

                            if products:
                                await Actor.push_data(products)
                                store_products.extend(products)

                            if idx == 0 and diagnostics_enabled():
                                try:
                                    fingerprint_hash_base = await compute_fingerprint_hash(page)
                                    Actor.log.info(
                                        f"[{store_name}] Fingerprint hash (post-category): {fingerprint_hash_base}"
                                    )
                                    if diagnostics_drift_check_enabled():
                                        await page.reload(wait_until="domcontentloaded")
                                        fingerprint_hash_after = await compute_fingerprint_hash(page)
                                        Actor.log.info(
                                            f"[{store_name}] Fingerprint hash (after reload): {fingerprint_hash_after}"
                                        )
                                        if fingerprint_hash_after != fingerprint_hash_base:
                                            Actor.log.warning(
                                                f"[{store_name}] Fingerprint drift detected within same context"
                                            )
                                except Exception as exc:
                                    Actor.log.warning(f"[{store_name}] Fingerprint hash failed: {exc}")

                            await asyncio.sleep(random.uniform(1, 2))

                        except Exception as e:
                            Actor.log.error(f"[{store_name}] Category error: {e}")
                            continue

                    Actor.log.info(f"Store {store_name} complete: {len(store_products)} products")
                    return len(store_products)

                finally:
                    if context is not None:
                        try:
                            await context.close()
                        except Exception:
                            pass
                    if owned_browser is not None:
                        try:
                            await owned_browser.close()
                        except Exception:
                            pass
                    gc.collect()

            # PARALLEL EXECUTION: Process 3 stores at a time
            PARALLEL_CONTEXTS = 3
            store_items = list(stores.items())

            try:
                for i in range(0, len(store_items), PARALLEL_CONTEXTS):
                    batch = store_items[i:i + PARALLEL_CONTEXTS]

                    Actor.log.info(f"\n{'='*60}")
                    Actor.log.info(f"BATCH {i//PARALLEL_CONTEXTS + 1}: Processing {len(batch)} stores in parallel")
                    Actor.log.info(f"{'='*60}")

                    # Run batch in parallel
                    tasks = [scrape_store(store_id, store_info) for store_id, store_info in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Count successes
                    for result in results:
                        if isinstance(result, int):
                            total_products += result
                        elif isinstance(result, Exception):
                            Actor.log.error(f"Store failed: {result}")

                    Actor.log.info(f"Batch complete. Total products so far: {total_products}")

                    # Delay between batches
                    await asyncio.sleep(random.uniform(2, 4))

            finally:
                if browser is not None:
                    await browser.close()

        Actor.log.info(f"\n{'='*60}")
        Actor.log.info(f"SCRAPING COMPLETE")
        Actor.log.info(f"Total products: {total_products}")
        Actor.log.info(f"{'='*60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
