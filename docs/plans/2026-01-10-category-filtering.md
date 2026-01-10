# Category Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a user-friendly `category_name` derived from the existing `category_url` (without touching scraper/worker), store it in the coordinator DB, forward it to Cheapskater, and make Cheapskater category filtering usable (human names, not numeric IDs).

**Architecture:** Coordinator computes `category_name = extract_category_name(category_url)` during `/api/v1/deals/bulk` ingestion (after validation, before DB upsert). Coordinator stores `category_name` (nullable) in its `deals` table and includes it in the forwarded payload to Cheapskater. Cheapskater prefers `category_name` when ingesting and uses it as its canonical `category` value for UI + API filtering.

**Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy (SQLite), Jinja templates.

---

### Task 1: Add coordinator category-name parsing tests (RED)

**Files:**
- Create: `test_category_name_extraction.py`

**Step 1: Write the failing test**
- Add test cases from `CATEGORY_FILTER_SPEC.md` covering:
  - `.../portable-fans/4294856700` → `Portable Fans`
  - `.../dishwasher-parts/554129471` → `Dishwasher Parts`
  - `.../rolled-fencing/barbed-wire/4294402516-4294401734` → `Barbed Wire`
  - `.../air-filters/4294761659-...` → `Air Filters`
  - numeric-only or empty → `Uncategorized`

**Step 2: Run test to verify it fails**
- Run: `python -m pytest -q test_category_name_extraction.py`
- Expected: FAIL (function/module not implemented yet).

---

### Task 2: Implement coordinator `category_name` flow (GREEN)

**Files:**
- Create: `apps/coordinator/coordinator_app/category_name.py`
- Modify: `apps/coordinator/coordinator_app/models.py`
- Modify: `apps/coordinator/coordinator_app/seed.py`
- Modify: `apps/coordinator/coordinator_app/web.py`

**Step 1: Implement `extract_category_name(category_url)`**
- Exact behavior (per spec):
  - Remove query string, trim trailing slash.
  - Split on `/pl/` then path `/`.
  - Remove purely-numeric segments (also numeric segments containing only digits and hyphens).
  - Take the last remaining slug segment and convert kebab-case → Title Case.
  - If nothing usable: return `"Uncategorized"`.

**Step 2: Make tests pass**
- Run: `python -m pytest -q test_category_name_extraction.py`
- Expected: PASS.

**Step 3: Add `category_name` column to coordinator Deal model**
- Add nullable `category_name` (`String(256)`) + an index on it.

**Step 4: Add a lightweight SQLite migration**
- In `create_tables()` add:
  - `ALTER TABLE deals ADD COLUMN category_name VARCHAR(256)` (best-effort, only if missing)
  - `CREATE INDEX IF NOT EXISTS idx_deals_category_name ON deals(category_name)`

**Step 5: Populate `category_name` during `/api/v1/deals/bulk`**
- In the existing ingestion loop:
  - compute `category_name = extract_category_name(d.category_url)`
  - include it in the `sqlite_insert(Deal).values(...)`
  - include it in the upsert `set_={...}` updates
  - include it in `accepted_deals.append({...})` forwarded to Cheapskater

**Step 6: Run the coordinator unit tests**
- Run: `python -m pytest -q test_category_name_extraction.py`

---

### Task 3: Add Cheapskater category-name parsing tests (RED)

**Files:**
- Create: `../CheapSkater-/tests/test_category_name_extraction.py`

**Step 1: Write failing tests**
- Mirror the coordinator cases, but targeting Cheapskater’s helper.

**Step 2: Verify tests fail**
- Run: `cd ../CheapSkater-; python -m pytest -q tests/test_category_name_extraction.py`
- Expected: FAIL.

---

### Task 4: Update Cheapskater ingest to accept `category_name` (GREEN)

**Files:**
- Modify: `../CheapSkater-/app/normalizers.py`
- Modify: `../CheapSkater-/app/ingest.py`
- Modify: `../CheapSkater-/app/dashboard.py`

**Step 1: Add `extract_category_name(category_url)` to `app/normalizers.py`**
- Same rules as coordinator.

**Step 2: Update ingest models**
- In `app/ingest.py`:
  - add optional `category_name: str | None = None` to `GloorbotDeal`
  - prefer `deal.category_name` when non-empty; else parse from `deal.category_url`
  - pass the chosen value as `category` into `repo.update_price_history(...)`
- In `app/dashboard.py`’s `/api/ingest` model:
  - add optional `category_name`
  - use preferred `category_name` similarly

**Step 3: Add API endpoints**
- Add `GET /api/categories` returning a sorted list of unique category names.
- Add `GET /api/deals?category=...` as a simple alias/wrapper around the existing `/api/clearance` data (or a minimal filtered listing), so clients have a straightforward category-filter endpoint.

**Step 4: Make tests pass**
- Run: `cd ../CheapSkater-; python -m pytest -q`

---

### Task 5: Verify end-to-end compatibility (no scraper/worker changes)

**Coordinator → Cheapskater forward payload**
- Ensure `category_name` is an additive field only (do not change worker payload or coordinator `/api/v1/deals/bulk` schema).

**Manual smoke (optional)**
- Start coordinator and Cheapskater locally; post a sample forwarded deal payload containing `category_url` + `category_name`; verify category dropdown shows human-readable labels.

