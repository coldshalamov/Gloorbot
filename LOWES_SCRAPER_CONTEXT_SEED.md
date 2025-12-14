# MISSION BRIEF: Lowe's Scraper "Ultra-Efficiency" Optimization

## 1. The Core Objective
We need to run a **Lowe's Inventory Scraper** on Apify that is **economically viable**.
- **Target Cost**: < $30 per full crawl (109,000 URLs).
- **Current Status**: Previous attempts were astronomically expensive ($400+) due to inefficient browser usage.
- **Goal**: Refactor, rewrite, or reinvent the scraper to run as lean as humanly possible while avoiding blocks.

## 2. The "Physics" of the Problem (Hard Constraints)
These are immutable facts discovered through painful trial and error. You CANNOT hallucinate your way around these:

1.  **Akamai Anti-Bot**: 
    - Blocks `headless=True` instantly (403 Forbidden).
    - Fingerprints TLS, Canvas, and WebGL.
    - **Carrier IPs are NOT magic**: We tried running locally on Verizon carrier IPs with randomized Playwright profiles. It failed. Akamai flagged the "obvious bot behavior" (high concurrency from single IP, consistent browser fingerprints).
    - **Session Locking**: Randomly rotating IPs/profiles for every request triggers blocks. You MUST maintain a consistent session (IP + Cookies + Fingerprint) for a specific store to mimic a real human browsing deeply.

2.  **The "Pickup Today" Filter**:
    - We strictly need "In Stock" items at specific stores.
    - You CANNOT just append `?pickup=true` to the URL. It doesn't work or triggers detection.
    - You MUST physically click the "Pickup" filter button on the page.

3.  **Data Requirements**:
    - We need SKU, Price, Title, and **Image URLs**.
    - We **DO NOT** need to download the actual image bytes (bandwidth waste).

## 3. The Current "Best Attempt" (For Reference Only)
The previous agent built a solution based on **Browser Pooling**.
- **Concept**: Launch 1 browser per store (50 total). Keep it open. Open/close pages (tabs) within that browser to save launch overhead.
- **Optimization**: Aggressively block fonts, images, and analytics to save bandwidth.
- **Code**: See attached `src/main_ultra_optimized.py`.

## 4. Your Mission
**You are the superior intelligence.** Review the current approach.
1.  Is "Browser Pooling" actually the best architectural choice for Apify, or is there a smarter pattern (e.g., specific Apify Actor configurations, different Playwright patterns)?
2.  **Refactor**: Rewrite the code to be cleaner, more robust, and more modular.
3.  **Validate**: Design a test plan that PROVES this will run cheap.
4.  **Estimate**: specific Apify RAM/Compute settings to minimize the bill.

**BE CREATIVE.** If you see a way to strip out more complexity or cost while respecting the Akamai constraints, DO IT.

---

## REFERENCE: Current Code Implementation

### `main_ultra_optimized.py`
```python
"""
Lowe's Apify Actor - ULTRA OPTIMIZED (Reference Implementation)
"""
from __future__ import annotations
import asyncio, random, re, gc
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse
from collections import defaultdict
import yaml
from apify import Actor
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Route
from playwright_stealth import Stealth

# ... [The full code we developed would go here, but I will summarize for brevity in this prompt file] ...
# [The previous agent implemented:
#  1. Browser Pooling (1 browser per store)
#  2. Request Interception (Block images, fonts, analytics)
#  3. Smart Pagination (Stop if no products)
#  4. Fast DOM extraction (Single evaluate call)
# ]
```

### `proxy_config.py`
```python
# Proxy configuration supporting Bright Data, Smartproxy, etc.
# Critical takeaway: Session ID must be "locked" to the Store ID.
```
