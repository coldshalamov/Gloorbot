# Lowe's Scraper DOM Inspection Report
## Date: 2026-01-06
## Test URL: https://www.lowes.com/pl/dishwashers/4294857925?goToProdList=true&inStock=1&rollUpVariants=0

---

## Executive Summary

**CRITICAL FINDING**: The scraper is returning **0 products** when the page actually contains **8 products** across **2 tile_groups**.

**Root Cause**: The scraper's JavaScript extraction logic is looking for a "Near Me" heading that **does not exist** on the current Lowe's page structure.

---

## DOM Inspection Results (Ground Truth)

### Anti-Detection Status
✅ **NOT BLOCKED** - _abck cookie contains `~-1~` (successful)

### Element Counts
- `div.tile_group`: **2**
- `[data-selector="splp-prd-act-$"]`: **8** (actual price elements)
- `[data-selector="splp-prd-promo-was-$"]`: **5** (was price elements)
- `[data-selector="splp-prd-ttl"]`: **8** (title elements)
- `[data-tile]`: **128** (individual product tiles)

### Sample Products Extracted from DOM

#### Product 1:
- **Title**: Frigidaire 24-in Top Control Built-in Dishwasher ( Fingerprint Resistant Stainless Steel ) , MaxDry andDishSense Technology , 52-Decibel
- **Actual Price**: `` (EMPTY - price element exists but aria-label is empty)
- **Was Price**: `Was Price $949.00`
- **Link**: https://www.lowes.com/pd/Frigidaire-Top-Control-24-in-Built-In-Dishwasher-Fingerprint-Resistant-Stainless-Steel-ENERGY-STAR-52-dBA/5014029863
- **Data-tile**: `1`

#### Product 2:
- **Title**: Bosch 300 Series 24-in Front Control Built-in Dishwasher ( Stainless Steel ) With Third Rack, PrecisionWash and PureDry , 50-Decibel
- **Actual Price**: `Actual Price $649.00`
- **Was Price**: `Was Price $529.00` ⚠️ **ANOMALY: Was price is HIGHER than actual price**
- **Link**: https://www.lowes.com/pd/Bosch-100-Series-Front-Control-Lowes-Exclusive-Dishwasher-in-Stainless-Steel-50DBA/5016138011
- **Data-tile**: `5`

---

## Scraper Output

**Products Found**: **0**

**Scraper Logs**:
```
[INFO] Found main grid container: [data-selector="splp-prd-lst"]
[INFO] Test Store - dishwashers p1: Empty (1/3), retrying...
[INFO] Found main grid container: [data-selector="splp-prd-lst"]
[INFO] Test Store - dishwashers p1: Empty (2/3), retrying...
[INFO] Found main grid container: [data-selector="splp-prd-lst"]
[INFO] Test Store - dishwashers: 3 consecutive empty pages, category done
```

---

## Root Cause Analysis

### Issue #1: Missing "Near Me" Heading (CRITICAL)

**Location**: `scraper.py` lines 903-905

```javascript
const nearMeHeading = hCandidates.find((h) => (h.textContent || "").toLowerCase().includes("near me"));
if (!nearMeHeading) return { ok: false, reason: "near_me_heading_not_found", products: [] };
```

**Problem**: The scraper's primary extraction method relies on finding a heading containing "near me" to scope the product extraction. **This heading does not exist** on the current Lowe's page structure.

**Evidence**: When the "Near Me" heading is not found, the JavaScript returns:
```javascript
{ ok: false, reason: "near_me_heading_not_found", products: [] }
```

This causes the scraper to fall back to the secondary extraction method, which also fails.

### Issue #2: Pickup Text Requirement (SECONDARY)

**Location**: `scraper.py` lines 854-858

```javascript
const pickupMatch = /pickup\\b/i.test(text) ? (text.match(/pickup[^.]{0,80}/i) || [])[0] : null;

// CRITICAL: only keep cards that show pickup availability.
// This avoids capturing non-local promotional carousels.
if (!pickupMatch) return null;
```

**Problem**: Even if the "Near Me" heading was found, the scraper requires each product card to contain the word "pickup" in its text content. This is overly restrictive and may filter out valid products.

### Issue #3: Price Extraction Anomalies

**Observation**: Product 1 has an **empty actual price** despite having a `[data-selector="splp-prd-act-$"]` element. The aria-label is empty.

**Observation**: Product 2 shows a **was price ($529) that is LOWER than the actual price ($649)**, which is illogical for a markdown. This suggests:
1. The prices might be swapped in the DOM
2. The "was price" might actually be a different type of price (e.g., online price vs. store price)
3. The scraper's price extraction logic needs validation

---

## Proposed Fixes (DO NOT IMPLEMENT - REPORT ONLY)

### Fix #1: Remove "Near Me" Heading Dependency

**Current Code** (lines 903-905):
```javascript
const nearMeHeading = hCandidates.find((h) => (h.textContent || "").toLowerCase().includes("near me"));
if (!nearMeHeading) return { ok: false, reason: "near_me_heading_not_found", products: [] };
```

**Proposed Fix**:
```javascript
// Option A: Make "Near Me" heading optional
const nearMeHeading = hCandidates.find((h) => (h.textContent || "").toLowerCase().includes("near me"));
const startElement = nearMeHeading || document.querySelector('[data-selector="splp-prd-lst"]') || document.body;

// Option B: Remove the heading requirement entirely and rely on the main grid container
// The scraper already finds [data-selector="splp-prd-lst"] successfully (see logs)
```

### Fix #2: Relax Pickup Text Requirement

**Current Code** (lines 854-858):
```javascript
const pickupMatch = /pickup\\b/i.test(text) ? (text.match(/pickup[^.]{0,80}/i) || [])[0] : null;
if (!pickupMatch) return null;
```

**Proposed Fix**:
```javascript
// Make pickup text optional since we're already filtering by the pickup filter in the URL
const pickupMatch = /pickup\\b/i.test(text) ? (text.match(/pickup[^.]{0,80}/i) || [])[0] : null;
// Remove the hard requirement - the pickup filter in the URL already ensures local inventory
// if (!pickupMatch) return null;  // REMOVE THIS LINE
```

### Fix #3: Validate Price Extraction Logic

**Investigation Needed**:
1. Why is Product 1's actual price aria-label empty?
2. Why is Product 2's "was price" lower than the "actual price"?
3. Are the `splp-prd-act-$` and `splp-prd-promo-was-$` selectors correctly mapped to current/was prices?

**Proposed Action**:
- Add logging to capture the raw aria-label values for debugging
- Validate that the selectors match Lowe's current DOM structure
- Consider adding fallback extraction methods if aria-label is empty

---

## Verification Steps

To confirm these fixes would work:

1. **Test the main grid container**: The logs show `[data-selector="splp-prd-lst"]` is being found successfully
2. **Verify tile_group extraction**: The DOM shows 2 `div.tile_group` elements exist
3. **Confirm pickup filter is applied**: The URL contains `inStock=1` parameter
4. **Validate product data**: 8 products with titles and links are present in the DOM

---

## Conclusion

The scraper is **functionally broken** due to a hard dependency on a "Near Me" heading that no longer exists in Lowe's current page structure. The DOM contains valid product data that the scraper cannot access.

**Immediate Action Required**:
1. Remove or make optional the "Near Me" heading requirement
2. Relax the pickup text requirement (already filtered by URL parameter)
3. Investigate price extraction anomalies

**Expected Outcome After Fixes**:
- Scraper should extract 8 products from the test page
- Prices should be correctly mapped to actual/was values
- No dependency on page headings that may change
