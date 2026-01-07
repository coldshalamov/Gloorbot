# Lowe’s Price Debugging + Evaluation Plan (Gloorbot)

Date: 2026-01-07

## Goal
Eliminate “scrambled” deals where `price` and/or `was_price` are unrelated to the real product price (e.g. financing snippets like `$125/mo` being interpreted as product price).

## Current Fix (Baseline)
Baseline fix is in `PARALLEL/scraper.py`:
- `extract_prices_from_card()` prefers `aria-label` “Actual Price $…” / “Was Price $…”
- filters financing/monthly-payment noise
- writes maximum-verbosity diagnostics (JSONL) when enabled

Worker defense-in-depth is in `apps/worker/src/gloorbot_worker/slot_worker.py`:
- `_to_float_price()` rejects financing/monthly-payment strings

## How to Enable “Maximum Verbose” Diagnostics
Set env var:
- `GLOORBOT_PRICE_DIAGNOSTICS=1`

Optional:
- `GLOORBOT_PRICE_DIAG_MAXLEN=1200` (increase per-line truncation)
- Worker auto-writes per-slot JSONL under `logs/price_diagnostics/slot_<id>.jsonl`

Each record includes:
- `product_url`/`product_href` (best effort)
- `title` (best effort)
- `canonical_now_count` / `canonical_was_count`
- `aria_label_count`
- `steps[]` with accept/reject reasoning and truncated raw inputs

## Evaluation Strategy (Don’t Burn Akamai)

### Track A: Offline HTML fixtures (preferred)
1. Collect failing examples as HTML snapshots:
   - Save the *product card HTML* for a known bad deal.
   - Save a *minimal reduced fixture* reproducing the bug (like the tests do).
2. For each fixture, assert:
   - `extract_prices_from_card()` returns expected `price` and `was_price`
   - diagnostics JSONL contains:
     - at least one “accepted” step
     - rejects financing candidates

This can run in CI without any network access.

### Track B: Low-rate Playwright “truth” runs (careful)
Goal: validate DOM assumptions on real pages with a warm profile.
- Pick 5–10 URLs and run **slowly** (sleep + minimal navigation).
- Prefer `/pl/` pages with `storeNumber=` and pickup filters (existing pipeline).
- On each run:
  - extract via DOM selectors/aria-labels
  - compare to scraper outputs
  - save artifacts: screenshot + HTML + diagnostics JSONL

Stop early if titles indicate “Access Denied”.

## What Another Agent Should Investigate Next
1. **Confirm remaining failure modes**
   - cards without `[data-selector="splp-prd-act-$"]`
   - aria-label variations (e.g. “Now $…”, “Sale Price $…”, localization)
   - tile_group edge cases (multiple `data-tile` products vs single)
2. **Audit JS extraction**
   - ensure it never falls back to scanning entire card text for `$` values
3. **Propose additional fixture tests**
   - credit card offer blocks
   - savings blocks (“Save $874.99”) + percent-off noise
   - monthly-payment blocks in multiple forms (`$125/mo`, `$167 per month`, etc.)

## Delegation (Swarm)
- **Agent A (DOM/DevTools)**: Use Chrome DevTools to list the most reliable selectors/aria-labels for now/was on both `/pl/` and `/pd/`. Deliver: selector guidance + 3–5 HTML snippets.
- **Agent B (Test harness)**: Build a small runner that loads HTML fixtures and emits a summary report (pass/fail + captured diagnostics).
- **Agent C (Pipeline sanity)**: Verify coordinator/worker ingest isn’t swapping `price`/`was_price` fields in transit; add logging at boundaries if needed.

