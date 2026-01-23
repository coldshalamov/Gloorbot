# Changelog - January 22, 2026

## Fix: Price Parsing for High-Value Items (>$1,000)

### Issue
Items over $1,000 were being mispriced (e.g., $1,071.83 showing as $16,371.00).
Causes identified:
1.  **Concatenation**: `textContent` was merging star ratings (1), review counts (637), and price parts ($1,071.83) into single strings like "16371.00".
2.  **Regex Limitation**: The regex `\d{1,3}(?:,\d{3})*` strictly required commas for thousands, failing on some CSS-rendered prices or partial matches.
3.  **Cents Inference**: The heuristic to treat 4-digit numbers as cents (e.g. 1637 -> 16.37) was aggressive and sometimes wrong for whole dollar amounts or concatenated strings.

### Changes

#### `PARALLEL/scraper.py`
*   **Updated `firstMoney` Regex**: Changed to `/\$\s*\d+(?:,\d{3})*(?:\.\d{2}|\d{2})?/g` to support prices >= 1000 even if commas are missing or malformed in the text stream.
*   **New `pickMoneyFromEl` Helper**:
    *   Prioritizes `aria-label` (cleanest source).
    *   Falls back to `innerText` (preserves visual separation) instead of `textContent` (merges text nodes).
*   **Improved Selector Specificity**:
    *   `extractCard` and `extractTileGroupProducts` now prefer `[data-testid="current-price"]`, `[data-testid="was-price"]`, etc., over generic selectors.
    *   Explicitly uses `pickMoneyFromEl` for extraction to enforce the `aria-label` > `innerText` priority.
*   **Scoring Logic**: `firstMoney` now collects all candidates and scores them, preferring those with decimal points or commas, and using numeric value as a tie-breaker (preferring the larger "Was" price over "Savings" amounts).

#### `apps/worker/src/gloorbot_worker/slot_worker.py`
*   **Conservative Cents Inference**: Increased the threshold for inferring cents from raw digits from 4 to 5.
    *   Old: `1234` -> `$12.34`
    *   New: `1234` -> `$1234.00` (unless it has a dot/comma)
    *   New: `12345` -> `$123.45`
    *   This prevents `2699` (price) from becoming `26.99`, while still catching `163710` -> `1637.10`.

#### `apps/worker/src/gloorbot_worker/__init__.py`
*   **Version Bump**: Updated version to `0.11.10` to reflect these changes.

### Verification
*   Reproduction script confirmed that the mock HTML for the "Wayne Dalton Garage Door" (which triggered the 16371.00 bug) now correctly parses as:
    *   Now: $1,071.83
    *   Was: $1,637.00
*   Samsung washer case ($2,296.99 / $3,597.99) also parses correctly.
