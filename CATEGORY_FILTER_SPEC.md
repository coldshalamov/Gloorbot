# Category Filtering Strategy for Cheapskater Website

## THE GOLDEN RULE: DO NOT BREAK THE WORKING SCRAPER

**CRITICAL**: The scraper pipeline is **100% functional** and has been battle-tested. It successfully:
- Scrapes Lowe's with Playwright without getting blocked
- Extracts prices correctly
- Filters deals at 50%+ markdown
- Sends deals to coordinator → Cheapskater → displays on website

**YOU MUST NOT MODIFY**:
- ❌ `PARALLEL/scraper.py` - Core scraping logic
- ❌ `apps/worker/src/gloorbot_worker/slot_worker.py` - Worker deal filtering and submission
- ❌ The deal submission payload format (don't add/remove/rename fields)
- ❌ The coordinator's deal ingestion endpoint (`POST /api/v1/deals/bulk`)
- ❌ Anything related to Playwright, price extraction, or Akamai evasion

**YOU MAY ONLY**:
- ✅ Add new columns to database tables (with migrations)
- ✅ Add logic to **parse existing data** (like `category_url`) into new fields
- ✅ Modify the Cheapskater website's frontend/backend to filter by category
- ✅ Add category name extraction logic in the coordinator's **existing ingestion flow** (after the deal is validated but before it's stored)

---

## The Problem

**Current State:**
The `category_url` field is successfully flowing through the entire pipeline:

```
Worker (slot_worker.py:392)
  ↓ creates deal dict with category_url
  ↓ POST /api/v1/deals/bulk
Coordinator (web.py:636)
  ↓ stores deal.category_url in SQLite
  ↓ forwards to Cheapskater
Cheapskater
  ↓ stores in /var/data/orwa_lowes.sqlite
  ↓ displays on website (but no category filtering exists)
```

**The Issue:**
The `category_url` field contains raw URLs from `PARALLEL/urls.txt`, which look like this:

```
https://www.lowes.com/pl/air-conditioners-fans/portable-fans/4294856700
https://www.lowes.com/pl/appliance-parts-accessories/dishwasher-parts/554129471
https://www.lowes.com/pl/fencing-gates/rolled-fencing/barbed-wire/4294402516-4294401734
https://www.lowes.com/pl/air-filters-accessories/air-filters/4294761659-4294760493-4294760441
```

**Problems with these URLs:**
1. **Inconsistent format**: Some have readable slugs (`air-conditioners-fans/portable-fans`), others just have category IDs (`4294856700`)
2. **Nested paths**: Multi-level categories like `fencing-gates/rolled-fencing/barbed-wire`
3. **Query params**: Some have complex query strings with multiple category codes
4. **Not user-friendly**: You can't show "https://www.lowes.com/pl/air-conditioners-fans/portable-fans/4294856700" as a filter option

**What Users Want:**
Clean category names like:
- "Portable Fans"
- "Dishwasher Parts"
- "Barbed Wire Fencing"
- "Air Filters"

---

## Data Flow Map

### Current Data Flow (✅ WORKING - DO NOT BREAK)

```
┌─────────────────────────────────────────────────────┐
│ 1. PARALLEL/urls.txt                                 │
│    Source of truth for what gets scraped            │
│    Format: One category URL per line                │
│    Example: https://www.lowes.com/pl/.../4294856700 │
└─────────────────────────────────────────────────────┘
            ↓ Read by worker
┌─────────────────────────────────────────────────────┐
│ 2. Worker (slot_worker.py)                           │
│    Line 392: Creates deal dict                       │
│    {                                                 │
│      "category_url": category_url,  ← RAW URL       │
│      "product_url": "...",                           │
│      "title": "...",                                 │
│      "price": 49.99,                                 │
│      "was_price": 129.99,                            │
│      "pct_off": 0.615                                │
│    }                                                 │
└─────────────────────────────────────────────────────┘
            ↓ POST /api/v1/deals/bulk
┌─────────────────────────────────────────────────────┐
│ 3. Coordinator (web.py:636)                          │
│    Stores in coordinator.sqlite:                    │
│    deals table:                                      │
│      - category_url (String 2048) ← RAW URL         │
│      - product_url, title, price, was_price, etc.   │
└─────────────────────────────────────────────────────┘
            ↓ Forward to Cheapskater (web.py:691)
┌─────────────────────────────────────────────────────┐
│ 4. Cheapskater Website                               │
│    POST /api/ingest/deals                            │
│    Stores in /var/data/orwa_lowes.sqlite            │
│    Same schema: category_url = RAW URL              │
└─────────────────────────────────────────────────────┘
            ↓ Website displays deals
┌─────────────────────────────────────────────────────┐
│ 5. Public Website (cheapskater.onrender.com)        │
│    Shows all deals in one big list                  │
│    NO CATEGORY FILTERING (the feature we need!)     │
└─────────────────────────────────────────────────────┘
```

---

## Solution Options

### Option 1: Parse Category Name On-The-Fly (Fastest Implementation)

**Where**: Cheapskater backend API (when serving deals to frontend)

**How**:
1. Query deals from SQLite (existing logic)
2. For each deal, parse `category_url` to extract human-readable name
3. Add `category_name` to the API response (doesn't exist in DB)
4. Frontend gets both `category_url` (raw) and `category_name` (parsed)

**Category Extraction Logic**:
```python
def extract_category_name(category_url: str) -> str:
    """
    Parse category URL to get human-readable name.

    Examples:
    - https://www.lowes.com/pl/air-conditioners-fans/portable-fans/4294856700
      → "Portable Fans"
    - https://www.lowes.com/pl/fencing-gates/rolled-fencing/barbed-wire/4294402516
      → "Barbed Wire"
    - https://www.lowes.com/pl/appliance-parts-accessories/dishwasher-parts/554129471
      → "Dishwasher Parts"
    """
    if not category_url:
        return "Uncategorized"

    try:
        # Remove query params and parse path
        path = category_url.split('?')[0].rstrip('/')
        segments = path.split('/pl/')[-1].split('/')

        # Filter out numeric segments (category IDs)
        text_segments = [s for s in segments if not s.replace('-', '').isdigit()]

        if not text_segments:
            return "Uncategorized"

        # Take the last text segment (most specific category)
        slug = text_segments[-1]

        # Convert kebab-case to Title Case
        return slug.replace('-', ' ').title()
    except:
        return "Uncategorized"
```

**Pros**:
- ✅ No database migration needed
- ✅ Works immediately with existing data
- ✅ Zero risk to scraper pipeline

**Cons**:
- ❌ Slight CPU overhead on every API call
- ❌ Can't efficiently query "show me all deals in category X" (no DB index)
- ❌ Parsing logic could fail on weird URLs

---

### Option 2: Add `category_name` Column (Cleaner, Better Performance)

**Where**: Coordinator's deal ingestion logic

**How**:
1. Add `category_name` column to `deals` table in coordinator DB
2. When coordinator receives deals from worker (web.py:636), extract category name from `category_url` **before storing**
3. Store both `category_url` (raw) and `category_name` (parsed)
4. Forward `category_name` to Cheapskater along with other deal fields
5. Cheapskater also adds `category_name` column and stores it
6. Frontend filters by `category_name` (clean, indexed column)

**Database Changes**:

**Coordinator** (`apps/coordinator/coordinator_app/models.py`):
```python
class Deal(Base):
    __tablename__ = "deals"
    # ... existing fields ...
    category_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category_name: Mapped[str | None] = mapped_column(String(256), nullable=True)  # NEW
```

**Coordinator ingestion** (`apps/coordinator/coordinator_app/web.py:636`):
```python
# BEFORE storing the deal, extract category name
category_name = extract_category_name(d.category_url)  # Use parsing logic from Option 1

base = sqlite_insert(Deal).values(
    store_id=d.store_id,
    store_name=d.store_name,
    category_url=d.category_url,
    category_name=category_name,  # NEW - store parsed name
    product_url=d.product_url,
    # ... rest of fields ...
)
```

**Forward to Cheapskater** (`apps/coordinator/coordinator_app/web.py:691`):
```python
accepted_deals.append({
    "store_id": d.store_id,
    "store_name": d.store_name,
    "category_url": d.category_url,
    "category_name": category_name,  # NEW - include in forwarded payload
    "product_url": d.product_url,
    # ... rest of fields ...
})
```

**Cheapskater** (add same `category_name` column to its schema and store it)

**Pros**:
- ✅ Fast queries: `SELECT DISTINCT category_name FROM deals` gives instant list
- ✅ Indexed column for efficient filtering
- ✅ No runtime parsing overhead
- ✅ Clear, semantic schema

**Cons**:
- ❌ Requires database migration
- ❌ Slightly more complex initial setup

---

## Recommended Approach

**Go with Option 2** (add `category_name` column) because:
1. The website will need to query "all deals in category X" efficiently
2. The "get all unique categories" query will be instant with an indexed column
3. It's the right long-term architecture
4. Migration is simple (just add nullable column, backfill can happen lazily)

---

## Implementation Checklist for Codex

### Phase 1: Coordinator Changes
- [ ] Add `category_name` column to `Deal` model in `apps/coordinator/coordinator_app/models.py`
- [ ] Write migration or use SQLAlchemy's `create_all()` to add column
- [ ] Add category extraction function (use the logic above)
- [ ] In `web.py:636`, extract `category_name` from `category_url` before storing deal
- [ ] In `web.py:691`, include `category_name` in the forwarded payload to Cheapskater

### Phase 2: Cheapskater Changes (Different Repo!)
**Repo**: `C:\Users\User\Documents\GitHub\Telomere\CheapSkater-`
- [ ] Add `category_name` column to Cheapskater's deal schema
- [ ] Update ingestion endpoint to accept and store `category_name`
- [ ] Add API endpoint: `GET /api/categories` → returns list of unique category names
- [ ] Add API endpoint: `GET /api/deals?category={name}` → filter deals by category
- [ ] Update frontend to show category filter dropdown
- [ ] Display deals grouped/filtered by category

### Phase 3: Testing
- [ ] Verify old deals without `category_name` still work (nullable column)
- [ ] Verify new deals get `category_name` populated
- [ ] Verify category filter on website works
- [ ] Verify no disruption to scraper pipeline

---

## Example Category URLs and Expected Names

| Raw `category_url` | Extracted `category_name` |
|-------------------|--------------------------|
| `https://www.lowes.com/pl/air-conditioners-fans/portable-fans/4294856700` | `Portable Fans` |
| `https://www.lowes.com/pl/appliance-parts-accessories/dishwasher-parts/554129471` | `Dishwasher Parts` |
| `https://www.lowes.com/pl/fencing-gates/rolled-fencing/barbed-wire/4294402516-4294401734` | `Barbed Wire` |
| `https://www.lowes.com/pl/air-filters-accessories/air-filters/4294761659` | `Air Filters` |
| `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/4294737274` | `Bathtubs` |

---

## Final Notes

**DO NOT**:
- Touch the scraper
- Touch the worker's deal creation logic
- Change the structure of deals being sent to the coordinator
- Modify price extraction or filtering logic

**DO**:
- Add new database columns (safe, additive change)
- Parse existing data into more useful formats
- Build the website filtering UI using the new `category_name` field

The scraper is a black box that produces `category_url` strings. Your job is to **consume and transform that data** without touching the producer.
