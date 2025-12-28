r"""
Cheapskater Ingest API - Add this to the Cheapskater app to receive deals from Gloorbot.

Copy this file to your Cheapskater repo as: app/ingest.py

Then add to dashboard.py:
    from app.ingest import router as ingest_router
    app.include_router(ingest_router)
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# These imports assume you're in the Cheapskater app
# from app.storage import repo
# from app.storage.db import make_session
# from app.storage.models_sql import Store, StorePriceHistory

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# Set this environment variable to secure the endpoint
INGEST_API_KEY = os.getenv("CHEAPSKATER_INGEST_API_KEY", "")


class GloorbotDeal(BaseModel):
    """Deal format from Gloorbot coordinator."""
    store_id: str
    store_name: str
    category_url: str
    product_url: str
    title: str
    price: float
    was_price: float
    pct_off: float
    found_at: str  # ISO8601 datetime


class IngestRequest(BaseModel):
    """Batch of deals from Gloorbot."""
    source: str = Field(default="gloorbot", description="Source system identifier")
    deals: list[GloorbotDeal]


class IngestResponse(BaseModel):
    ok: bool
    accepted: int
    errors: int = 0
    message: str = ""


def extract_sku_from_url(product_url: str) -> str | None:
    """Extract SKU from Lowe's product URL.

    Examples:
        https://www.lowes.com/pd/Product-Name/5001844889 -> 5001844889
        https://www.lowes.com/pd/DEWALT-Drill/1234567 -> 1234567
    """
    # Pattern: /pd/something/NUMBERS at the end
    match = re.search(r'/pd/[^/]+/(\d+)', product_url)
    if match:
        return match.group(1)

    # Fallback: any trailing number sequence
    match = re.search(r'/(\d{6,})(?:\?|$)', product_url)
    if match:
        return match.group(1)

    return None


def extract_category_from_url(category_url: str) -> str:
    """Extract category name from Lowe's category URL.

    Examples:
        https://www.lowes.com/pl/Power-tools/4294857564 -> Power tools
        https://www.lowes.com/pl/Drill-bits--Power-tool-accessories/4294857975 -> Drill bits
    """
    # Pattern: /pl/Category-Name/numbers
    match = re.search(r'/pl/([^/]+)/\d+', category_url)
    if match:
        # Convert "Power-tools" to "Power Tools"
        raw = match.group(1)
        # Replace -- with separator, then - with space
        parts = raw.split('--')
        cleaned = parts[0].replace('-', ' ').strip()
        return cleaned.title()

    return "Clearance"  # Default category


def parse_store_info(store_id: str, store_name: str) -> dict[str, str]:
    """Parse store_name to extract city and state.

    Examples:
        "Seattle, WA (#0001)" -> city="Seattle", state="WA"
        "Portland #1234" -> city="Portland", state=""
    """
    city = ""
    state = ""

    # Pattern: "City, ST" or "City, ST (#NNNN)"
    match = re.match(r'^([^,]+),\s*([A-Z]{2})', store_name)
    if match:
        city = match.group(1).strip()
        state = match.group(2).strip()
    else:
        # Just use the name up to any # or (
        city = re.sub(r'\s*[#(].*', '', store_name).strip()

    return {"city": city, "state": state}


def convert_gloorbot_deal(deal: GloorbotDeal) -> dict[str, Any] | None:
    """Convert Gloorbot deal format to Cheapskater StorePriceHistory format."""

    sku = extract_sku_from_url(deal.product_url)
    if not sku:
        return None

    category = extract_category_from_url(deal.category_url)
    store_info = parse_store_info(deal.store_id, deal.store_name)

    # Parse timestamp
    try:
        ts = datetime.fromisoformat(deal.found_at.replace('Z', '+00:00'))
    except Exception:
        ts = datetime.now(timezone.utc)

    return {
        "retailer": "lowes",
        "store_id": deal.store_id,
        "store_name": deal.store_name,
        "store_city": store_info["city"],
        "store_state": store_info["state"],
        "sku": sku,
        "title": deal.title[:500],  # Truncate long titles
        "category": category,
        "price": deal.price,
        "price_was": deal.was_price,
        "pct_off": deal.pct_off,
        "availability": "In Stock",  # Gloorbot only finds in-stock items
        "product_url": deal.product_url,
        "image_url": None,  # Could be added later
        "clearance": True,
        "ts_utc": ts,
    }


# Uncomment this when integrating into Cheapskater:
"""
from app.storage.db import get_engine, make_session
from app.storage.models_sql import Store, StorePriceHistory

# Get database session (same pattern as dashboard.py)
DATABASE_FILE = Path(__file__).resolve().parent.parent / "orwa_lowes.sqlite"
engine = get_engine(str(DATABASE_FILE))
session_factory = make_session(engine)

def get_session():
    with session_factory() as session:
        yield session


@router.post("/deals", response_model=IngestResponse)
async def ingest_deals(
    request: IngestRequest,
    session: Session = Depends(get_session),
    x_api_key: str = Header(default=""),
):
    '''Receive deals from Gloorbot and insert into Cheapskater database.'''

    # Validate API key if configured
    if INGEST_API_KEY and x_api_key != INGEST_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    accepted = 0
    errors = 0

    for deal in request.deals:
        try:
            converted = convert_gloorbot_deal(deal)
            if not converted:
                errors += 1
                continue

            # Upsert store
            store = session.get(Store, converted["store_id"])
            if store is None:
                store = Store(
                    id=converted["store_id"],
                    name=converted["store_name"],
                    city=converted["store_city"],
                    state=converted["store_state"],
                    zip="",  # Not available from Gloorbot
                )
                session.add(store)

            # Update price history (same logic as repo.update_price_history)
            from app.storage.repo import update_price_history
            update_price_history(
                session,
                retailer=converted["retailer"],
                store_id=converted["store_id"],
                sku=converted["sku"],
                title=converted["title"],
                category=converted["category"],
                ts_utc=converted["ts_utc"],
                price=converted["price"],
                price_was=converted["price_was"],
                pct_off=converted["pct_off"],
                availability=converted["availability"],
                product_url=converted["product_url"],
                image_url=converted["image_url"],
                clearance=converted["clearance"],
            )

            accepted += 1

        except Exception as e:
            errors += 1
            continue

    session.commit()

    return IngestResponse(
        ok=True,
        accepted=accepted,
        errors=errors,
        message=f"Processed {len(request.deals)} deals"
    )
"""


# ============================================================================
# STANDALONE TEST MODE
# Run this file directly to test the conversion logic
# ============================================================================

if __name__ == "__main__":
    # Test data
    test_deals = [
        GloorbotDeal(
            store_id="0001",
            store_name="Seattle, WA (#0001)",
            category_url="https://www.lowes.com/pl/Power-tools/4294857564",
            product_url="https://www.lowes.com/pd/DEWALT-20V-MAX-Drill/5001844889",
            title="DEWALT 20V MAX 1/2-in Cordless Drill",
            price=79.00,
            was_price=159.00,
            pct_off=0.5031,
            found_at="2024-12-28T10:30:45.123456Z",
        ),
        GloorbotDeal(
            store_id="1234",
            store_name="Portland #1234",
            category_url="https://www.lowes.com/pl/Drill-bits--Power-tool-accessories/4294857975",
            product_url="https://www.lowes.com/pd/Some-Product/9876543",
            title="Some Great Product",
            price=25.00,
            was_price=50.00,
            pct_off=0.50,
            found_at="2024-12-28T11:00:00Z",
        ),
    ]

    print("Testing Gloorbot -> Cheapskater conversion:\n")
    for deal in test_deals:
        print(f"Input: {deal.title}")
        print(f"  URL: {deal.product_url}")

        converted = convert_gloorbot_deal(deal)
        if converted:
            print(f"  SKU: {converted['sku']}")
            print(f"  Category: {converted['category']}")
            print(f"  Store: {converted['store_city']}, {converted['store_state']}")
            print(f"  Price: ${converted['price']:.2f} (was ${converted['price_was']:.2f})")
            print(f"  OK!")
        else:
            print(f"  FAILED to convert")
        print()
