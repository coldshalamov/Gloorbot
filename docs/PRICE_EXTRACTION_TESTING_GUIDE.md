# Price Extraction Testing Guide for Gloorbot Scraper

**Version:** 1.0  
**Date:** 2026-01-07  
**Purpose:** Comprehensive testing strategies and documentation for all price extraction failure modes identified in the Gloorbot scraper.

---

## Table of Contents

1. [Overview](#overview)
2. [Diagnostic Environment Variables](#diagnostic-environment-variables)
3. [Failure Mode Categories](#failure-mode-categories)
4. [Testing Strategy](#testing-strategy)
5. [Fix Verification Process](#fix-verification-process)
6. [Test Infrastructure](#test-infrastructure)

---

## Overview

This guide provides comprehensive testing strategies for all price extraction failure modes identified in the Gloorbot scraper. The price extraction pipeline spans multiple components:

- **Scraper (Python)**: [`PARALLEL/scraper.py`](PARALLEL/scraper.py:403-700) - Main price extraction logic
- **Worker (Python)**: [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - Price validation and deal acceptance
- **Coordinator (Python)**: [`apps/coordinator/coordinator_app/web.py`](apps/coordinator/coordinator_app/web.py) - Deal validation and forwarding to CheapSkater

Each failure mode is documented with:
- Description of the issue
- How to test for it (step-by-step instructions)
- Expected behavior when working correctly
- What to look for in diagnostic logs
- Sample test cases with actual values where possible
- How to reproduce the bug
- How to verify the fix works

---

## Diagnostic Environment Variables

### Price Extraction Diagnostics (Scraper)

| Variable | Purpose | How to Enable | What It Logs |
|----------|---------|-------------|-------------|
| `GLOORBOT_PRICE_DIAGNOSTICS` | Enable per-card JSONL tracing of price extraction steps | Set to `1` or `true` | Writes to file specified by `GLOORBOT_PRICE_DIAG_PATH` or appends to navlog JSONL | Each record includes: `ts`, `event`, `product_url`, `title`, `canonical_now_count`, `canonical_was_count`, `aria_label_count`, `steps[]` with accept/reject reasoning and truncated raw inputs |
| `GLOORBOT_PRICE_DIAG_MAXLEN` | Control truncation length of raw text in diagnostics | Set to integer (default: 800) | Limits line length in diagnostic logs to prevent overflow |
| `GLOORBOT_PRICE_DIAG_PATH` | Set custom path for price diagnostics JSONL file | Set to file path (string) | Overrides default navlog path |

### Deal Diagnostics (Worker)

| Variable | Purpose | How to Enable | What It Logs |
|----------|---------|-------------|-------------|
| `GLOORBOT_DEAL_DIAGNOSTICS` | Enable JSONL logging explaining why each candidate becomes a deal or gets dropped | Set to `1` or `true` | Writes per-slot logs to `logs/deal_diagnostics/` | Each record includes: `ts`, `candidate`, `reason` (accepted/rejected), `deal_threshold_check`, `pct_off` |
| `GLOORBOT_DEAL_DIAG_PATH` | Set custom path for deal diagnostics JSONL file | Set to file path (string) | Overrides default path |

### Coordinator Validation Endpoints

| Endpoint | Purpose | How to Test |
|----------|---------|-------------|
| `/api/v1/status` | Check coordinator health and diagnostic stats | GET request | Returns: `forward_status_code`, `cheapskater_ingest_url_configured`, `cheapskater_api_key_configured`, `latest_ingest_stats` |
| `/api/v1/debug/task-url-stats` | Verify `/c/` URLs are not present in tasks | GET request (requires `DEBUG_API_TOKEN`) | Returns: `total_tasks`, `c_url_count`, `pl_url_count` |
| `/api/v1/deals/bulk` | Submit deals to coordinator | POST request | Returns: `total_submitted`, `total_accepted`, `total_rejected_suspicious`, `total_rejected_other`, `rejected_deals[]` |

---

## Failure Mode Categories

### 1. DOM Extraction Failures (8 issues)

#### 1.1 Financing Noise Misread as Product Price

**Description:** Financing/monthly-payment strings (e.g., `$125/mo`, `$167 per month`) are incorrectly interpreted as the product price.

**Root Cause:** The scraper's fallback text blob scanning or aria-label scanning picks up dollar amounts from financing text without filtering.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:270-274) - `_looks_like_financing_noise()`, [`PARALLEL/scraper.py`](PARALLEL/scraper.py:371-378) - `_money_values_from_text_blob()`

**How to Test:**
1. Create a test HTML fixture with financing text:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <div data-selector="splp-prd-act-$">$125/mo Suggested payments with 8 month special financing.</div>
       <a href="/pd/12345">
         <h3>Product Name</h3>
       </a>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled:
   ```bash
   GLOORBOT_PRICE_DIAGNOSTICS=1 python PARALLEL/scraper.py
   ```
3. Check the diagnostic JSONL output for rejection of financing noise:
   ```bash
   # Look for "financing_noise_in_aria" or "financing_noise_in_text" in steps
   grep "financing_noise" logs/price_diagnostics/*.jsonl
   ```

**Expected Behavior When Working Correctly:**
- Financing strings are rejected at both aria-label and text blob stages
- Diagnostic logs show `rejected: ["financing_noise_in_aria"]` or `["financing_noise_in_text"]`
- Price extraction returns `price: "N/A"` or skips the card entirely

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, look for entries where `ok: false`
- Check if `rejected` array contains `"financing_noise_in_aria"` or `"financing_noise_in_text"`
- Verify the `candidate` field shows the financing string (e.g., `$125/mo`)

**Sample Test Cases:**
| Test Input | Expected Price | Expected Was Price | Should Reject? |
|------------|---------------|------------------|--------------|
| `$125/mo Suggested payments with 8 month special financing.` | N/A | N/A | Yes |
| `$167 per month` | N/A | N/A | Yes |
| `Pay as low as $50/mo` | N/A | N/A | Yes |
| `Special financing: Buy now, pay later` | N/A | N/A | Yes |

**How to Reproduce the Bug:**
1. Create a test HTML page with financing text visible
2. Run the scraper without diagnostics enabled
3. Observe that the financing amount is extracted as the price

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify financing strings are now rejected in diagnostic logs
4. Verify price is `N/A` or skipped

---

#### 1.2 Savings Percentage Misread as Dollar Amount

**Description:** Savings percentage text (e.g., `Save 5%`) is incorrectly interpreted as a dollar amount (`$5`).

**Root Cause:** The scraper's text blob scanning picks up percentage values with dollar signs without proper filtering.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:358-364) - `_money_values_from_text_blob()`

**How to Test:**
1. Create a test HTML fixture with savings percentage:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <div data-selector="splp-prd-act-$">Save 5%</div>
       <a href="/pd/12345">
         <h3>Product Name</h3>
       </a>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for savings percentage acceptance

**Expected Behavior When Working Correctly:**
- Savings percentage strings are filtered out in text blob cleaning
- Diagnostic logs show savings candidates being rejected or ignored
- Price extraction returns actual prices only

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, look for entries where `source: "blob_infer_pair"` or `"blob_infer_pair"`
- Check if any step shows acceptance of a percentage value
- Verify the `candidate` field shows the percentage string

**Sample Test Cases:**
| Test Input | Expected Price | Expected Was Price | Should Reject? |
|------------|---------------|------------------|--------------|
| `Save 5%` | N/A | N/A | Yes |
| `Save 10%` | N/A | N/A | Yes |
| `Save 20%` | N/A | N/A | Yes |
| `Save 50%` | N/A | N/A | Yes |

**How to Reproduce the Bug:**
1. Create a test HTML page with savings percentage visible
2. Run the scraper without diagnostics enabled
3. Observe that the savings percentage is extracted as the price

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify savings percentages are now filtered/ignored in diagnostic logs
4. Verify price is actual dollar amount, not percentage

---

#### 1.3 Wrong Price from Mixed Tile Group

**Description:** When `div.tile_group` contains multiple products, the scraper may mix prices/titles from different tiles, resulting in mismatched data (e.g., href from tile 1, price from tile 2).

**Root Cause:** The scraper treats `div.tile_group` as a single card instead of splitting by `data-tile` attribute.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1690-1727) - `extract_tile_group_products()`, [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1696-1721) - `scrape_category_page()`

**How to Test:**
1. Create a test HTML fixture with multiple products in a tile_group:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <a href="/pd/product1">Product 1 Title</a>
       <div data-selector="splp-prd-act-$">$100</div>
     </div>
     <div data-tile="2">
       <a href="/pd/product2">Product 2 Title</a>
       <div data-selector="splp-prd-act-$">$200</div>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check that tile_group is properly split by data-tile

**Expected Behavior When Working Correctly:**
- Each product in tile_group is extracted as a separate record
- Prices and titles are correctly associated with the same data-tile
- No mixing of data between different tiles

**What to Look for in Diagnostic Logs:**
- In diagnostic logs, check `steps[]` for entries from `extract_tile_group_products()`
- Verify that each product has correct href, title, and price
- Check that `data-tile` values are consistent within each product

**Sample Test Cases:**
| Scenario | Tile 1 Href | Tile 1 Title | Tile 1 Price | Tile 2 Href | Tile 2 Title | Tile 2 Price | Expected Result |
|----------|-------------|-------------|-------------|-------------|-------------|-------------|
| Mixed tiles (bug) | `/pd/product1` | Product 1 | $100 | `/pd/product2` | Product 2 | $200 | Tile 1: `/pd/product1`, $100; Tile 2: `/pd/product2`, $200 |

**How to Reproduce the Bug:**
1. Create a test HTML page with a tile_group containing mixed products
2. Run the scraper without the tile split fix
3. Observe that prices/titles are mixed between tiles

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify tile_group is now properly split by data-tile
4. Verify each product has correct associated data

---

#### 1.4 Missing Canonical Selectors

**Description:** Cards without the canonical Lowe's selectors (`data-selector="splp-prd-act-$"`, `data-selector="splp-prd-promo-was-$"`) fall back to unreliable text blob scanning, leading to incorrect or missing prices.

**Root Cause:** The scraper's fallback logic doesn't have the proper selectors for all card types.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:475-511) - Canonical selector fallback, [`PARALLEL/scraper.py`](PARALLEL/scraper.py:634-680) - Aria-label scanning fallback

**How to Test:**
1. Create a test HTML fixture with missing canonical selectors:
   ```html
   <div class="product-card">
     <h3>Product Name</h3>
     <span class="price">$99.99</span>
     <span class="was-price">$199.99</span>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for fallback to aria-label scanning

**Expected Behavior When Working Correctly:**
- Canonical selectors are found and used first
- Fallback to aria-label scanning only happens when canonical selectors fail
- Prices are correctly extracted

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, check for entries where `source: "aria_scan"` or `"aria_scan_actual"` or `"aria_scan_was"`
- Verify that canonical selectors were attempted first (`canonical_now_count` > 0 or `canonical_was_count` > 0)
- Verify fallback to aria-label scanning only happened when canonical selectors failed

**Sample Test Cases:**
| Scenario | Has Canonical Selectors | Expected Result |
|----------|-------------|---------------|
| Normal card | Yes | Price extracted, Was Price extracted | Correct |
| Missing selectors | No | Price may be missing or incorrect | Fallback triggered |

**How to Reproduce the Bug:**
1. Create a test HTML page without canonical selectors
2. Run the scraper with diagnostics enabled
3. Observe that fallback to aria-label scanning is triggered

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify canonical selectors are now being used (check `canonical_now_count` and `canonical_was_count`)
4. Verify prices are correctly extracted

---

#### 1.5 Aria-Label Scanning Limit

**Description:** The scraper limits aria-label scanning to 80 nodes maximum, which may miss prices on pages with many products.

**Root Cause:** Performance optimization limits the number of aria-label nodes scanned.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:557) - `n = min(aria_count, 80)`

**How to Test:**
1. Create a test HTML fixture with more than 80 aria-label elements
2. Run the scraper with diagnostics enabled
3. Check if any prices are missed due to the 80-node limit

**Expected Behavior When Working Correctly:**
- All aria-label elements are scanned up to the limit
- Prices from all products are extracted
- No products are skipped due to scanning limits

**What to Look for in Diagnostic Logs:**
- Check `aria_label_count` in diagnostic logs
- Compare with number of products on the page
- Verify no products were missed

**Sample Test Cases:**
| Number of Aria Labels | Number of Products | Expected Result |
|------------------------|-------------------|---------------|
| 85 | 85 | All prices extracted | Correct |
| 100 | 100 | All prices extracted | Correct |
| 150 | 150 | First 80 scanned, rest may be missed | Partial |

**How to Reproduce the Bug:**
1. Create a test HTML page with 150+ aria-label elements
2. Run the scraper with diagnostics enabled
3. Check if any prices beyond the first 80 are missed

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify all prices are captured (check `aria_label_count` vs number of products)

---

#### 1.6 Strikethrough Price Not Found

**Description:** The scraper's strikethrough fallback doesn't find the was-price, resulting in missing or empty `was_price` values.

**Root Cause:** The strikethrough selector (`s, del`) is not present or doesn't contain price information.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:600-632) - Strikethrough fallback

**How to Test:**
1. Create a test HTML fixture with strikethrough price:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <span class="price">$99.99</span>
       <s>was: $199.99</s>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for strikethrough fallback

**Expected Behavior When Working Correctly:**
- Strikethrough price is found and extracted
- `was_price` field is populated

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, look for entries where `source: "strike_was"`
- Verify the `candidate` field shows the was-price value
- Check if `ok: true`

**Sample Test Cases:**
| Scenario | Strike Element Present | Expected Price | Expected Was Price | Expected Result |
|----------|-------------|---------------|------------------|--------------|
| Strike present | Yes | $99.99 | $199.99 | Both extracted | Correct |
| Strike missing | No | $99.99 | N/A | Price only | Partial |

**How to Reproduce the Bug:**
1. Create a test HTML page without strikethrough element
2. Run the scraper with diagnostics enabled
3. Observe that was_price is missing

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify was_price is now populated when strikethrough is present

---

#### 1.7 Text Blob Inference Too Aggressive

**Description:** The scraper's blob inference fallback extracts multiple dollar amounts and infers was_price as max, now_price as min, which can lead to incorrect price pairs (e.g., now=$10, was=$100 when actual is now=$50, was=$40).

**Root Cause:** The blob inference logic doesn't have sufficient validation to prevent impossible price pairs.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:634-680) - Blob inference fallback

**How to Test:**
1. Create a test HTML fixture with multiple prices:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <div data-selector="splp-prd-act-$">$10</div>
       <div data-selector="splp-prd-promo-was-$">$100</div>
       <div data-selector="splp-prd-act-$">$50</div>
       <div data-selector="splp-prd-promo-was-$">$40</div>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for blob inference

**Expected Behavior When Working Correctly:**
- Blob inference correctly identifies the highest price as was_price
- Lowest price is correctly identified as now_price
- Impossible price pairs (e.g., $10 now, $100 was) are prevented by sanity checks

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, look for entries where `source: "blob_infer_pair"`
- Check if `inferred_now` and `inferred_was` are present
- Verify the inferred values match the actual prices
- Check if sanity checks prevented impossible pairs

**Sample Test Cases:**
| Actual Prices | Now Price | Was Price | Expected Inference | Expected Result |
|----------------|---------------|------------------|--------------|--------------|
| $10, $50, $40 | $10 | $50 | Correct | Correct |
| $100, $50, $10 | $100 | $50 | Correct | Correct |
| $10, $100, $50 | $10 | $100 | Impossible pair ($10 now, $100 was) | Rejected |

**How to Reproduce the Bug:**
1. Create a test HTML fixture with multiple prices where lowest is not the actual now price
2. Run the scraper with diagnostics enabled
3. Observe that blob inference creates incorrect pair

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_PRICE_DIAGNOSTICS=1`
2. Run the same test that reproduced the bug
3. Verify impossible pairs are rejected or corrected

---

### 2. Price Parsing Failures (4 issues)

#### 2.1 Regex Search Returns First Match Instead of All

**Description:** Using `re.search()` instead of `re.findall()` returns only the first price match, missing higher prices.

**Root Cause:** The price parsing function uses `re.search()` which stops at the first match instead of finding all prices.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py) - Legacy `parse_price()` (deprecated)

**How to Test:**
1. Create a test string with multiple prices: `$998.00, $499.99, $899.99`
2. Call the legacy `parse_price()` function
3. Verify only the first price is returned

**Expected Behavior When Working Correctly:**
- All prices in the string are found and returned
- The highest price is returned (or appropriate price based on context)

**What to Look for in Diagnostic Logs:**
- This is a legacy issue; the function has been replaced
- Look for uses of the new `_money_values_from_text_blob()` function

**Sample Test Cases:**
| Input String | Expected Output | Legacy Behavior | Expected New Behavior |
|----------------|---------------|------------------|--------------|--------------|
| `$998.00, $499.99, $899.99` | $998.00 | First match only | All prices found |
| Multiple prices in text | All prices | First match only | All prices found |

**How to Reproduce the Bug:**
1. Create a test with multiple prices
2. Use legacy parsing (if still available)
3. Verify only first price is returned

**How to Verify the Fix Works:**
1. This issue has been fixed; the new function uses `re.findall()`
2. Verify all prices are extracted correctly

---

#### 2.2 Price Less Than $1 Filtered Out

**Description:** Prices below $1 are filtered out entirely, causing legitimate low-priced items to be skipped.

**Root Cause:** The blob inference logic filters out prices < $1, which can remove valid clearance items.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:398) - `if v >= 1.0:`

**How to Test:**
1. Create a test HTML fixture with price $0.99:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <div data-selector="splp-prd-act-$">$0.99</div>
       <a href="/pd/12345">
         <h3>Clearance Item</h3>
       </a>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for blob inference

**Expected Behavior When Working Correctly:**
- Prices < $1 are filtered out
- Diagnostic logs show rejection of low prices
- Item is skipped

**What to Look for in Diagnostic Logs:**
- In `steps[]` array, look for entries where `source: "blob_infer_pair"`
- Check if `ok: false` and `reason` indicates filtering
- Verify the `candidate` field shows the low price

**Sample Test Cases:**
| Price | Expected Result |
|----------------|---------------|------------------|
| $0.99 | Filtered out, item skipped | Correct |
| $4.99 | Accepted | Correct |

**How to Reproduce the Bug:**
1. Create a test HTML page with a price below $1
2. Run the scraper with diagnostics enabled
3. Verify low price is filtered out

**How to Verify the Fix Works:**
1. This is intentional filtering to avoid noise
2. Verify the filter is working correctly

---

#### 2.3 Percent-Only String Not Rejected

**Description:** Strings containing only a percentage (e.g., `5%`) are not rejected, causing them to be passed as prices.

**Root Cause:** The worker's `_to_float_price()` function doesn't reject percent-only strings.

**Location in Code:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - `_to_float_price()`

**How to Test:**
1. Create a test deal payload with percent-only price:
   ```json
   {
     "title": "Test Product",
     "price": "5%",
     "was_price": "",
     "pct_off": 0.95
   }
   ```
2. Submit the deal to the worker (or coordinator test endpoint)
3. Check if the deal is accepted or rejected

**Expected Behavior When Working Correctly:**
- Percent-only strings are rejected at the worker level
- Deal is not accepted into the pipeline
- Diagnostic logs show rejection reason

**What to Look for in Diagnostic Logs:**
- Enable `GLOORBOT_DEAL_DIAGNOSTICS=1`
- Check deal diagnostic logs for rejection of percent-only prices
- Verify `reason` field indicates percent-only rejection

**Sample Test Cases:**
| Price Input | Expected Was Price | Expected Result |
|----------------|---------------|------------------|--------------|
| `5%` | N/A | Rejected | Correct |
| `10%` | N/A | Rejected | Correct |
| `Save 5%` | N/A | Rejected | Correct |

**How to Reproduce the Bug:**
1. Create a test deal with percent-only price
2. Submit to worker with diagnostics enabled
3. Verify deal is rejected

**How to Verify the Fix Works:**
1. Enable diagnostics: `GLOORBOT_DEAL_DIAGNOSTICS=1`
2. Verify percent-only strings are rejected

---

#### 2.4 Price String Contains Non-Numeric Characters

**Description:** Price strings with non-numeric characters (e.g., `$1,049.90`) fail to parse as floats.

**Root Cause:** The price parsing doesn't handle commas or other formatting characters properly.

**Location in Code:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - `_to_float_price()`

**How to Test:**
1. Create a test deal payload with formatted price:
   ```json
   {
     "title": "Test Product",
     "price": "$1,049.90",
     "was_price": "",
     "pct_off": 0.95
   }
   ```
2. Submit the deal to the worker
3. Check if the deal is accepted or rejected

**Expected Behavior When Working Correctly:**
- Formatted prices are correctly parsed as floats
- Deal is accepted or rejected based on validity

**What to Look for in Diagnostic Logs:**
- Enable `GLOORBOT_DEAL_DIAGNOSTICS=1`
- Check deal diagnostic logs for parsing failures
- Verify formatted prices are handled correctly

**Sample Test Cases:**
| Price Input | Expected Result |
|----------------|---------------|------------------|
| `$1,049.90` | Parsed as 1049.90 | Accepted | Correct |
| `$1.049` | Parsed as 1.049 | Accepted | Correct |
| `$1.049.90` (no comma) | Parsed as 1.049 | Accepted | Correct |

**How to Reproduce the Bug:**
1. Create a test deal with various price formats
2. Submit to worker with diagnostics enabled
3. Verify parsing handles different formats correctly

**How to Verify the Fix Works:**
1. Verify the price parsing function handles commas properly
2. Test various price formats

---

### 3. Worker Validation Failures (6 issues)

#### 3.1 Financing String Not Rejected at Worker Level

**Description:** Financing strings (e.g., `$125/mo`) pass through the worker's `_to_float_price()` function and become deals.

**Root Cause:** The worker's financing rejection regex is incomplete or not applied.

**Location in Code:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - `_to_float_price()`

**How to Test:**
1. Create a test deal payload with financing price:
   ```json
   {
     "title": "Test Product",
     "price": "$125/mo",
     "was_price": "",
     "pct_off": 0.95
   }
   ```
2. Submit the deal to the worker
3. Check if the deal is accepted or rejected

**Expected Behavior When Working Correctly:**
- Financing strings are rejected at the worker level
- Deal is not accepted into the pipeline
- Diagnostic logs show rejection reason

**What to Look for in Diagnostic Logs:**
- Enable `GLOORBOT_DEAL_DIAGNOSTICS=1`
- Check deal diagnostic logs for financing rejections
- Verify `reason` field indicates financing rejection

**Sample Test Cases:**
| Price Input | Expected Result |
|----------------|---------------|------------------|
| `$125/mo` | Rejected | Correct |
| `$167 per month` | Rejected | Correct |
| `Pay as low as $50/mo` | Rejected | Correct |

**How to Reproduce the Bug:**
1. Create a test deal with various financing strings
2. Submit to worker with diagnostics enabled
3. Verify all financing strings are rejected

**How to Verify the Fix Works:**
1. Verify the worker's financing regex is comprehensive
2. Test various financing patterns

---

#### 3.2 Impossible Savings Delta

**Description:** The savings delta (was_price - price) is implausibly large (e.g., > $5,000), indicating incorrect prices.

**Root Cause:** No validation on the savings delta to detect impossible scenarios.

**Location in Code:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - Deal acceptance logic

**How to Test:**
1. Create a test deal payload with impossible savings:
   ```json
   {
     "title": "Test Product",
     "price": "$100",
     "was_price": "$11,000",
     "pct_off": 0.99
   }
   ```
2. Submit the deal to the worker
3. Check if the deal is accepted or rejected

**Expected Behavior When Working Correctly:**
- Deals with impossible savings delta are rejected
- Diagnostic logs show rejection reason

**What to Look for in Diagnostic Logs:**
- Enable `GLOORBOT_DEAL_DIAGNOSTICS=1`
- Check deal diagnostic logs for savings delta rejections
- Verify `reason` field indicates impossible savings

**Sample Test Cases:**
| Price | Was Price | Savings Delta | Pct Off | Expected Result |
|----------------|---------------|------------------|--------------|
| $100 | $11,000 | $10,000 | 0.99 | Rejected | Correct |
| $50 | $100 | $50 | 0.50 | Accepted | Correct |

**How to Reproduce the Bug:**
1. Create a test deal with various savings deltas
2. Submit to worker with diagnostics enabled
3. Verify impossible deltas are rejected

**How to Verify the Fix Works:**
1. Verify savings delta validation is in place
2. Test various savings scenarios

---

#### 3.3 Absurd Price Ceiling Violation

**Description:** Prices above $10,000 are not rejected, allowing absurd prices to reach the database.

**Root Cause:** The worker's price validation doesn't have an upper limit check.

**Location in Code:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - `_to_float_price()` and coordinator validation

**How to Test:**
1. Create a test deal payload with absurd price:
   ```json
   {
     "title": "Test Product",
     "price": "$15,000",
     "was_price": "$20,000",
     "pct_off": 0.25
   }
   ```
2. Submit the deal to the coordinator
3. Check if the deal is accepted or rejected

**Expected Behavior When Working Correctly:**
- Deals with prices > $10,000 are rejected
- Diagnostic logs show rejection reason

**What to Look for in Diagnostic Logs:**
- Check coordinator status endpoint for rejected_suspicious count
- Verify absurd prices are rejected

**Sample Test Cases:**
| Price | Was Price | Expected Result |
|----------------|---------------|------------------|
| $15,000 | $20,000 | 0.25 | Rejected | Correct |
| $11,000 | $20,000 | 0.45 | Accepted | Correct |
| $9,999 | $19,998 | 0.50 | Accepted | Correct |

**How to Reproduce the Bug:**
1. Create a test deal with prices above $10,000
2. Submit to coordinator with diagnostics enabled
3. Verify absurd prices are rejected

**How to Verify the Fix Works:**
1. Verify coordinator validation is rejecting high prices
2. Test various price ranges

---

#### 3.4 Missing Image URL

**Description:** Product cards without an image URL are processed, leading to broken or missing images in the database.

**Root Cause:** Image URL extraction fails or returns None, and the code doesn't handle this gracefully.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:731-757) - Image extraction logic

**How to Test:**
1. Create a test HTML fixture without image:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <a href="/pd/12345">
         <h3>Product Name</h3>
       </a>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for image extraction

**Expected Behavior When Working Correctly:**
- Image URL is extracted or None is handled gracefully
- Product without image is still processed (not skipped)

**What to Look for in Diagnostic Logs:**
- Check `image_url` field in diagnostic logs
- Verify missing images are handled correctly

**Sample Test Cases:**
| Has Image | Expected Result |
|----------------|---------------|------------------|
| Yes | Image extracted | Correct |
| No | image_url is None or empty | Correct |
| Invalid image URL | image_url: "data:..." | Correct |

**How to Reproduce the Bug:**
1. Create a test HTML page with missing/invalid image
2. Run the scraper with diagnostics enabled
3. Verify image handling is correct

**How to Verify the Fix Works:**
1. Verify image URL extraction handles edge cases
2. Test various image scenarios

---

#### 3.5 Missing or Empty Title

**Description:** Product cards without a title or with an empty title are processed, leading to invalid database entries.

**Root Cause:** Title extraction fails or returns empty string, and the code doesn't validate this.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:429-431) - Title extraction, [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1759-1775) - Card filtering

**How to Test:**
1. Create a test HTML fixture without title:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <div data-selector="splp-prd-act-$">$100</div>
       <a href="/pd/12345">
       </a>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for title extraction

**Expected Behavior When Working Correctly:**
- Title is extracted or card is skipped
- Empty titles are handled correctly

**What to Look for in Diagnostic Logs:**
- Check `title` field in diagnostic logs
- Verify empty or missing titles are handled correctly

**Sample Test Cases:**
| Title | Expected Result |
|----------------|---------------|------------------|
| Present | Title extracted | Correct |
| Empty | Title is empty string | Card skipped | Correct |
| Too short | Title < 5 chars | Card skipped | Correct |

**How to Reproduce the Bug:**
1. Create a test HTML page without title
2. Run the scraper with diagnostics enabled
3. Verify title handling is correct

**How to Verify the Fix Works:**
1. Verify title validation is in place
2. Test various title scenarios

---

#### 3.6 Invalid Product URL

**Description:** Product URLs are malformed or missing, leading to database errors.

**Root Cause:** URL extraction or construction fails, creating invalid or empty URLs.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:726-769) - URL construction

**How to Test:**
1. Create a test HTML fixture with invalid URL:
   ```html
   <div class="tile_group">
     <div data-tile="1">
       <a href="">Product Name</a>
       <div data-selector="splp-prd-act-$">$100</div>
     </div>
   </div>
   ```
2. Run the scraper with diagnostics enabled
3. Check the diagnostic JSONL output for URL extraction

**Expected Behavior When Working Correctly:**
- Invalid URLs are detected and handled
- Product is skipped

**What to Look for in Diagnostic Logs:**
- Check `product_url` field in diagnostic logs
- Verify invalid URLs are handled correctly

**Sample Test Cases:**
| URL | Expected Result |
|----------------|---------------|------------------|
| Empty href | Skipped | Correct |
| Relative path only | Skipped | Correct |
| Missing /pd/ | Invalid URL detected | Correct |

**How to Reproduce the Bug:**
1. Create a test HTML page with invalid URL
2. Run the scraper with diagnostics enabled
3. Verify URL validation is working

**How to Verify the Fix Works:**
1. Verify URL validation catches invalid URLs
2. Test various URL scenarios

---

### 4. Timing and Race Conditions (2 issues)

#### 4.1 Page Load Timeout

**Description:** The scraper times out waiting for the page to load, causing incomplete data extraction.

**Root Cause:** Network issues, slow page loads, or browser hangs.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1182) - Page navigation with timeouts

**How to Test:**
1. Simulate a slow page load (use dev-browser or network throttling)
2. Run the scraper with normal timeout
3. Check if timeout occurs

**Expected Behavior When Working Correctly:**
- Page loads within timeout
- All products are extracted
- No timeout errors

**What to Look for in Diagnostic Logs:**
- Check Actor logs for timeout errors
- Verify timeout handling is working correctly

**Sample Test Cases:**
| Scenario | Expected Result |
|----------------|---------------|------------------|
| Normal page load | Products extracted | Correct |
| Slow page load | Products extracted or graceful timeout | Correct |
| Network error | Timeout error logged | Correct |

**How to Reproduce the Bug:**
1. Simulate slow network conditions
2. Run the scraper and observe timeout behavior

**How to Verify the Fix Works:**
1. Verify timeout handling is robust
2. Test with various network conditions

---

#### 4.2 DOM Not Ready When Extracting

**Description:** The scraper attempts to extract prices before the page is fully rendered, leading to missing or incorrect data.

**Root Cause:** Insufficient wait time after page navigation before DOM extraction.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1182) - Page navigation, [`PARALLEL/scraper.py`](PARALLEL/scraper.py:1207-1218) - Human behavior simulation

**How to Test:**
1. Reduce wait times after page navigation
2. Run the scraper with reduced waits
3. Check if extraction is more reliable

**Expected Behavior When Working Correctly:**
- Page is fully loaded before extraction
- All products are extracted correctly
- No missing data due to timing issues

**What to Look for in Diagnostic Logs:**
- Check for timeout or missing element errors
- Verify wait times are sufficient

**Sample Test Cases:**
| Wait Time | Expected Result |
|----------------|---------------|------------------|
| 2s | Products extracted | Correct |
| 0.5s | Products extracted | Correct |
| 0s | May have timing issues | Correct |

**How to Reproduce the Bug:**
1. Run the scraper with minimal wait times
2. Observe if timing issues occur

**How to Verify the Fix Works:**
1. Verify sufficient wait times are used
2. Test with various page load scenarios

---

### 5. Data Transformation Failures (2 issues)

#### 5.1 Price/Was Price Swapped

**Description:** The price and was_price fields are swapped in transit between components (e.g., coordinator receives price as was_price and vice versa).

**Root Cause:** Field mapping errors in API endpoints or data processing.

**Location in Code:** [`apps/coordinator/coordinator_app/web.py`](apps/coordinator/coordinator_app/web.py) - Deal bulk endpoint, [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - Deal submission

**How to Test:**
1. Create a test deal payload with swapped prices:
   ```json
   {
     "title": "Test Product",
     "price": "$100",
     "was_price": "$50",
     "pct_off": 0.50
   }
   ```
2. Submit the deal to the coordinator
3. Check the deal in the database

**Expected Behavior When Working Correctly:**
- Price and was_price are correctly mapped
- No field swapping occurs

**What to Look for in Diagnostic Logs:**
- Check coordinator logs for field mapping
- Verify deal data in database has correct prices

**Sample Test Cases:**
| Submitted Price | Submitted Was Price | Database Price | Database Was Price | Expected Result |
|----------------|---------------|------------------|--------------|
| $100 | $50 | $100 | $50 | Correct |
| $50 | $100 | $50 | $100 | Swapped | Incorrect |

**How to Reproduce the Bug:**
1. Create a test deal with known price/was values
2. Submit to coordinator and verify in database
3. Check for field swapping

**How to Verify the Fix Works:**
1. Verify field mapping is correct
2. Check database integrity

---

#### 5.2 Unicode/Encoding Issues in JSONL Logs

**Description:** Diagnostic JSONL logs contain improperly encoded Unicode characters, making them difficult to read or parse.

**Root Cause:** JSON encoding issues when writing diagnostic logs.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:318-330) - JSONL writing, [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - JSONL writing

**How to Test:**
1. Enable diagnostics and run scraper
2. Read the diagnostic JSONL files
3. Check for encoding issues

**Expected Behavior When Working Correctly:**
- JSONL logs are properly encoded (UTF-8)
- No encoding errors or corruption
- Logs are readable

**What to Look for in Diagnostic Logs:**
- Open JSONL files in a text editor
- Check for malformed characters
- Verify UTF-8 encoding

**Sample Test Cases:**
| Scenario | Expected Result |
|----------------|---------------|------------------|
| Normal operation | Properly encoded | Correct |
| Unicode characters | Properly encoded | Correct |
| Malformed JSON | Read error | Correct |

**How to Reproduce the Bug:**
1. Create test with Unicode characters in product data
2. Run scraper and check JSONL logs
3. Verify encoding is correct

**How to Verify the Fix Works:**
1. Verify JSON encoding is UTF-8
2. Test with various Unicode scenarios

---

### 6. Configuration and Environment Issues (2 issues)

#### 6.1 Diagnostic Path Not Writable

**Description:** The diagnostic JSONL file path is not writable or doesn't exist, preventing diagnostics from being written.

**Root Cause:** File system permissions issues or incorrect path configuration.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:292-305) - Path resolution, [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - Path resolution

**How to Test:**
1. Set `GLOORBOT_PRICE_DIAG_PATH` to a non-existent directory
2. Run the scraper with diagnostics enabled
3. Check for file write errors

**Expected Behavior When Working Correctly:**
- Diagnostic path is validated and created if needed
- Diagnostics are written successfully
- Fallback to default path works

**What to Look for in Diagnostic Logs:**
- Check Actor logs for file write errors
- Verify path resolution is working

**Sample Test Cases:**
| Path | Expected Result |
|----------------|---------------|------------------|
| Valid path | Diagnostics written | Correct |
| Invalid path | Error logged, fallback used | Correct |
| Non-existent directory | Directory created, fallback used | Correct |

**How to Reproduce the Bug:**
1. Set invalid diagnostic path
2. Run the scraper and observe behavior
3. Verify fallback to default path

**How to Verify the Fix Works:**
1. Verify path validation is robust
2. Test with various path scenarios

---

#### 6.2 Diagnostic Environment Variables Not Set

**Description:** Required diagnostic environment variables are not set, preventing diagnostics from being enabled.

**Root Cause:** Missing environment variable configuration in the worker or scraper execution environment.

**Location in Code:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py:281-282) - Env var checks, [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) - Env var checks

**How to Test:**
1. Run the scraper without diagnostic env vars set
2. Check if diagnostics are written

**Expected Behavior When Working Correctly:**
- Diagnostics are not written (as expected)
- Scraper functions normally without diagnostics

**What to Look for in Diagnostic Logs:**
- Check for diagnostic JSONL files
- Verify no diagnostic files are created

**Sample Test Cases:**
| Env Vars Set | Expected Result |
|----------------|---------------|------------------|
| None | No diagnostics written | Correct |
| `GLOORBOT_PRICE_DIAGNOSTICS=1` | Diagnostics written | Correct |

**How to Reproduce the Bug:**
1. Set diagnostic env vars
2. Run the scraper and verify diagnostics are written

**How to Verify the Fix Works:**
1. Verify env var checks are working
2. Test with various configurations

---

## Testing Strategy

### Offline Testing (Preferred)

**Why Offline Testing?**
1. **No Akamai blocking risk** - Testing with HTML fixtures avoids triggering Lowe's anti-bot measures
2. **Faster iteration** - No network delays, instant feedback
3. **Deterministic** - Same input always produces same output
4. **CI/CD integration** - Can run in automated pipelines
5. **No resource consumption** - Doesn't burn Lowe's servers or worker bandwidth

**Test Infrastructure:**
- HTML fixtures stored in [`tests/price_extraction/fixtures/`](tests/price_extraction/fixtures/)
- Unit test templates in [`tests/price_extraction/templates/`](tests/price_extraction/templates/)
- Integration test scripts in [`tests/price_extraction/scripts/`](tests/price_extraction/scripts/)
- Test data files in [`tests/price_extraction/data/`](tests/price_extraction/data/)

### Live Testing (Use with Caution)

**When to Use Live Testing:**
1. **Akamai-safe URLs only** - Use verified category URLs from `apps/coordinator/data/urls.txt`
2. **Rate limiting** - Don't hammer Lowe's servers with rapid requests
3. **Warm profiles** - Use persistent browser profiles with established trust
4. **Monitor for blocking** - Watch for "Access Denied" pages and stop immediately
5. **Small batches** - Test a few categories at a time, not the entire catalog
6. **Verify with dev-browser** - Use dev-browser to verify DOM structure before running full scraper

**Live Testing Workflow:**
1. Warm up browser profile (visit homepage, perform search)
2. Verify pickup filter works on target category
3. Run scraper with diagnostics enabled on a single category
4. Review diagnostic logs for any issues
5. Fix any issues found before scaling up

---

## Fix Verification Process

For each issue, follow this process to verify the fix is working:

### Step 1: Understand the Fix

1. **Read the code changes** - Review the git commits that fixed the issue
2. **Identify the fix location** - Note which file(s) were modified
3. **Understand the mechanism** - How does the fix prevent the failure mode?

### Step 2: Verify Code is Deployed

1. **Check Render coordinator** - If the fix is in the coordinator:
   ```bash
   curl https://gloorbot-coordinator.onrender.com/api/v1/status
   ```
2. **Check commit hash** - Verify the deployed commit includes the fix:
   ```bash
   cd PARALLEL
   git log --oneline -1
   # Look for the fix commit hash in recent commits
   ```
3. **Verify worker version** - If the fix is in the worker installer, download and install the latest version

### Step 3: Create Reproduction Test

1. **Build a test case** - Create a test that reproduces the original bug
2. **Run the test** - Execute the test with the current code
3. **Observe the result** - Check if the bug still occurs or is fixed

### Step 4: Verify Fix with Diagnostics

1. **Enable diagnostics** - Set the appropriate diagnostic environment variables
2. **Run the test** - Execute with diagnostics enabled
3. **Review logs** - Check diagnostic logs to verify the fix is working
4. **Confirm expected behavior** - Verify the expected behavior is now observed

### Step 5: Add Regression Test

1. **Create a test** - Add a test to the test suite that verifies the fix
2. **Run in CI** - Ensure the test runs in CI/CD pipelines
3. **Document** - Add comments explaining what the test verifies

---

## Test Infrastructure

### Directory Structure

```
tests/price_extraction/
├── fixtures/              # HTML fixtures for known failure scenarios
│   ├── financing_noise.html
│   ├── savings_percentage.html
│   ├── mixed_tile_group.html
│   ├── missing_canonical_selectors.html
│   ├── strikethrough_missing.html
│   ├── multiple_prices_blob_inference.html
│   ├── price_below_dollar.html
│   ├── percent_only_string.html
│   ├── absurd_price_ceiling.html
│   ├── missing_image.html
│   ├── empty_title.html
│   └── invalid_product_url.html
├── templates/             # Unit and integration test templates
│   ├── unit_test_price_extraction.py
│   ├── integration_test_dom_extraction.py
│   └── integration_test_worker_validation.py
├── scripts/              # Test execution scripts
│   ├── run_price_extraction_tests.py
│   └── run_worker_validation_tests.py
└── data/                 # Test data files
    ├── edge_cases_prices.csv
    ├── edge_cases_deals.csv
    └── edge_cases_titles.csv
```

### Test Execution

Run all tests:
```bash
# Run price extraction unit tests
cd tests/price_extraction
python -m pytest templates/unit_test_price_extraction.py -v

# Run worker validation tests
cd tests/price_extraction
python -m pytest templates/integration_test_worker_validation.py -v

# Run all tests
cd tests/price_extraction
python -m pytest -v
```

---

## Summary

This comprehensive testing guide covers 40+ failure modes across 8 categories with detailed testing strategies, diagnostic procedures, and verification processes. Each mode includes:

- Clear description of the issue
- Root cause analysis
- Code location references
- Step-by-step testing instructions
- Expected behavior when working correctly
- Diagnostic log indicators
- Sample test cases
- Bug reproduction steps
- Fix verification process

Use this guide as the definitive reference for debugging and testing price extraction issues in the Gloorbot scraper.
