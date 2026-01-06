#!/usr/bin/env python3
"""
Local test of Lowe's scraper with 5% discount threshold.

This validates that the aria-label price extraction fix is working
by running a single category with a much lower discount threshold
so we can see if it's grabbing the correct price fields.

Usage:
    python test_lowes_prices_5pct.py --store-id 2250 --category-url "https://www.lowes.com/pl/Washers/4294677814"

Or set environment variable:
    DEAL_THRESHOLD=0.05 python test_lowes_prices_5pct.py
"""

import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add PARALLEL to path so we can import the scraper
sys.path.insert(0, str(Path(__file__).parent / "PARALLEL"))

try:
    from scraper import (
        SmokeTestConfig,
        scrape_category,
        get_canonical_store_url,
        create_akamai_context,
    )
except ImportError as e:
    print(f"ERROR: Could not import PARALLEL scraper: {e}")
    print("Make sure you're running from the repo root")
    sys.exit(1)


DEAL_THRESHOLD = float(os.getenv("DEAL_THRESHOLD", "0.05"))

_PRICE_RE = re.compile(r"\$?\s*([0-9]{1,5})(?:[.,]\s*([0-9]{2}))?")


def to_float_price(text: str) -> Optional[float]:
    """Convert price text to float (same logic as slot_worker)."""
    if not text:
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


def filter_deals(products: list[dict], threshold: float) -> list[dict]:
    """Filter products by discount threshold (same logic as slot_worker)."""
    deals = []

    for p in products:
        price_now = to_float_price(str(p.get("price", "")))
        was_price = to_float_price(str(p.get("price_was", "")))

        if not price_now or not was_price or was_price <= 0:
            continue

        # Guard against parse errors
        if was_price >= 200 and price_now <= 10:
            continue

        # Ensure price is actually discounted
        if price_now >= was_price:
            continue

        pct_off = (was_price - price_now) / was_price

        # Additional sanity checks
        if was_price >= 200 and pct_off > 0.97:
            continue
        if was_price >= 10000:
            continue
        if (was_price - price_now) > 5000:
            continue

        # Apply threshold
        if pct_off < threshold:
            continue

        deals.append({
            **p,
            "pct_off": round(pct_off, 4),
            "discount_pct": f"{pct_off*100:.1f}%",
        })

    return deals


async def main():
    store_id = sys.argv[1] if len(sys.argv) > 1 else "2250"
    category_url = (
        sys.argv[2] if len(sys.argv) > 2
        else "https://www.lowes.com/pl/Washers/4294677814"
    )

    print(f"Testing Lowe's scraper with {DEAL_THRESHOLD*100:.1f}% discount threshold")
    print(f"Store ID: {store_id}")
    print(f"Category: {category_url}")
    print("-" * 80)

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            config = SmokeTestConfig(
                store_id=store_id,
                category_url=category_url,
                pages_to_test=1,  # Just one page for quick test
                headless=False,
                verbose=True,
            )

            context = await create_akamai_context(pw, headless=False)
            page = await context.new_page()

            print(f"\n[1] Setting up store context...")
            store_url = get_canonical_store_url(store_id)
            await page.goto(store_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            print(f"[2] Scraping category...")
            products = await scrape_category(
                page,
                category_url=category_url,
                store_id=store_id,
                max_items=100,  # Get enough to test
            )

            print(f"[3] Extracted {len(products)} total products")
            if products:
                print("\nFirst product (raw):")
                p = products[0]
                for key in ["title", "price", "price_was", "url"]:
                    print(f"  {key}: {p.get(key)}")

            # Filter by threshold
            deals = filter_deals(products, DEAL_THRESHOLD)
            print(f"\n[4] Filtered to {len(deals)} deals (>{DEAL_THRESHOLD*100:.1f}% off)")

            if deals:
                print("\nTop 5 deals:")
                for i, deal in enumerate(deals[:5], 1):
                    title = deal.get("title", "Unknown")[:50]
                    price = f"${deal.get('price', 0):.2f}"
                    was = f"${deal.get('price_was', 0):.2f}"
                    pct = deal.get("discount_pct", "?")
                    print(f"  {i}. {title}")
                    print(f"     Price: {price} (was {was}) - {pct} off")
                    print()
            else:
                print("\nNo deals found at this threshold!")
                if products:
                    print("\nProducts by discount:")
                    for p in products[:5]:
                        was = to_float_price(str(p.get("price_was", "")))
                        now = to_float_price(str(p.get("price", "")))
                        if was and now and was > now:
                            pct = (was - now) / was
                            print(f"  {p.get('title', 'Unknown')[:40]}: {pct*100:.1f}% off")

            await page.close()
            await context.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
