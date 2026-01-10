# Removal of Deal Rejection Filters

## Summary

Removed all arbitrary deal rejection filters from the worker and coordinator. The system now captures all deals that have valid price data, allowing full visibility into what the scraper is actually capturing.

## Rationale

If the scraping logic is working correctly, rejection filters serve no purpose except hiding garbage data. The correct approach is to:
1. Let the scraper capture everything
2. See what it actually finds
3. Fix the scraper if the data is bad

This way, you get complete visibility into scraping bugs instead of silent rejections.

## Changes Made

### Worker (`apps/worker/src/gloorbot_worker/slot_worker.py`)

**Removed filters**:
- ❌ `high_ticket_tiny_price` - Rejected if `was_price >= $200` AND `price_now <= $10`
- ❌ `suspicious_extreme_pct_off` - Rejected if `was_price >= $200` AND discount `> 97%`
- ❌ `absurd_was_price` - Rejected if `was_price >= $10,000`
- ❌ `absurd_savings_delta` - Rejected if savings `> $5,000`
- ❌ `below_threshold` - Rejected if discount `< 50%`

**Kept filter**:
- ✅ `missing_or_invalid_price` - Still rejects if price extraction completely failed

**Result**: Lines 263-379 simplified to just extract `price_now`, `was_price`, validate they exist, and calculate `pct_off`.

### Coordinator (`apps/coordinator/coordinator_app/web.py`)

**Removed filters** (all defense-in-depth duplicates of the worker checks):
- ❌ High-ticket tiny price check
- ❌ Extreme pct_off check
- ❌ Absurd was_price check
- ❌ Absurd savings delta check
- ❌ Below threshold rejection

**Kept tracking**:
- ✅ `below_threshold` counter - Still counts deals below 50% for metrics, but doesn't reject them

**Result**: Lines 600-632 simplified to just count below-threshold deals for logging, then accept all deals.

## Data Flow Impact

### Before
```
Worker scrapes product
  ↓
Apply 5 rejection filters
  ↓
Coordinator receives only "clean" deals
  ↓
Apply 5 more rejection filters (defense-in-depth)
  ↓
Store in database (filtered data)
  ↓
Website shows filtered data
```

### After
```
Worker scrapes product
  ↓
Only reject if prices are completely missing/invalid
  ↓
Coordinator receives all deals with valid prices
  ↓
Store in database (all data)
  ↓
Website shows all deals
  ↓
Diagnostics logs capture why deals were filtered (if enabled)
```

## Metrics Impact

The coordinator still tracks:
- `received_count` - Total deals received
- `unique_count` - After de-duplication
- `below_threshold` - Deals with discount < 50% (tracked but NOT rejected)
- `rejected_suspicious` - Now always 0 (field kept for backward compatibility)
- `upserted` - Deals stored in database (was much lower before, now equals unique_count)

## Testing

Before deploying:
1. Run a scrape with a single category
2. Check `coordinator.sqlite` deals table - should see ALL products, including:
   - Products with discounts < 50%
   - Expensive items with extreme discounts
   - Edge cases that were previously filtered
3. Check `logs/deal_diagnostics/` for any actually malformed data
4. Verify Cheapskater website receives and displays all deals

## Rollback

If you find that storing unfiltered data causes issues:
1. Revert the two edits above
2. Restore the reject conditions
3. Analyze the diagnostics to understand what the scraper is actually capturing

But the goal is to fix the scraper, not hide its output.

## Next Steps

With full visibility into scraper output:
1. Monitor for patterns in "bad" deals
2. Update price extraction logic if needed
3. Add category filtering on the website (already in progress)
4. Consider data quality metrics for monitoring
