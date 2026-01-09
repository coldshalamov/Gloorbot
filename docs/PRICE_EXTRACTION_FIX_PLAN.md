# Gloorbot Price Extraction Fix Plan
**Document Version:** 1.0  
**Date:** 2026-01-09  
**Status:** PLANNING (Not Implemented)

---

## Executive Summary

Gloorbot scraper ([`PARALLEL/scraper.py`](PARALLEL/scraper.py)) has a complex 5-strategy fallback system for price extraction that occasionally produces incorrect prices in production, while CheapSkater uses a simpler 3-selector approach that works reliably. All deterministic tests pass (100% pass rate), but diagnostic logging is **DISABLED** in the worker environment, making it impossible to identify the actual production failures. This plan analyzes the root causes and provides two fix strategies with clear implementation guidance.

---

## 1. Root Cause Analysis

### 1.1 Why Tests Pass But Production Fails

**Key Finding:** All 4 deterministic regression tests pass with 100% success rate, yet production workers still report wrong prices.

**Root Cause:** The tests validate the **code logic** works correctly, but they don't validate that:
1. The **worker environment** has the latest code fixes
2. Diagnostic logging is **enabled** to capture actual production failures
3. The worker is using the **correct version** of PARALLEL/scraper.py

**Evidence:**
- [`verification/run_suite.py`](verification/run_suite.py) runs 4 deterministic tests that all pass
- Tests validate: tile_group splitting, financing noise rejection, price extraction logic
- However, [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) shows diagnostic logging is **disabled by default** (lines 37-39, 161-174)
- Environment variables `GLOORBOT_PRICE_DIAGNOSTICS` and `GLOORBOT_DEAL_DIAGNOSTICS` are not set in production
- Worker installed at `C:\Users\User\AppData\Local\GloorbotWorker` may be running an older version without recent fixes

### 1.2 Gloorbot's 5-Strategy Price Extraction System

Gloorbot's [`extract_prices_from_card()`](PARALLEL/scraper.py:403-732) uses a **5-strategy fallback system**:

| Strategy | Description | Priority | Used When |
|----------|-------------|----------|------------|
| **Strategy 1: data-testid** | Primary (first) | Always - uses `[data-testid='current-price']`, `[data-testid='regular-price']`, `[data-testid='was-price']` |
| **Strategy 2: Canonical Selectors** | Fallback (if Strategy 1 fails) | Uses `[data-selector='splp-prd-act-$']`, `[data-selector='splp-prd-promo-was-$']` |
| **Strategy 3: Aria-label Scan** | Fallback (if Strategies 1-2 fail) | Scans all `[aria-label]` attributes for "Actual Price" / "Was Price" patterns |
| **Strategy 4: Strikethrough** | Fallback (if Strategy 3 fails) | Looks for `<s>` or `<del>` elements |
| **Strategy 5: Blob Inference** | Last resort (if all others fail) | Extracts all `$` values from card text, infers `$now/$was` pair |

**Why This System Is Problematic:**
1. **Complexity:** 5 strategies increase code complexity and potential for bugs
2. **Selector Priority:** Lower-priority strategies (2-5) can match wrong elements before higher-priority ones
3. **Inference Risks:** Strategy 5 (blob inference) can misinterpret unrelated `$` values (e.g., "$125/mo", shipping thresholds)
4. **No Diagnostic Visibility:** Without `GLOORBOT_PRICE_DIAGNOSTICS=1`, we cannot see which strategy is actually failing in production

### 1.3 CheapSkater's 3-Selector Approach

CheapSkater uses a **simplified, proven approach**:

```python
# CheapSkater price extraction (simplified, proven working)
1. Try data-testid current-price
2. Try data-testid regular-price  
3. Try data-testid was-price
```

**Why CheapSkater Works:**
1. **Simplicity:** Only 3 selectors, all with explicit semantic meaning
2. **No Inference:** No blob parsing that can misinterpret text
3. **No Fallback Chain:** Doesn't cascade through multiple strategies that can pick wrong elements
4. **Proven Reliability:** Works consistently in production

### 1.4 Known Issues Already Fixed

From [`AGENTS.md`](agents.md) milestones, the following issues have been **identified and fixed**:

| Issue | Date | Root Cause | Fix Applied | Status |
|--------|------|-------------|---------|--------|
| Financing noise (`$125/mo` misread as price) | 2026-01-07 | Added financing noise filtering in [`extract_prices_from_card()`](PARALLEL/scraper.py:403) | **FIXED** |
| Tile group mixing (href/title from product A + price from product B) | 2026-01-07 | Split `div.tile_group` by `data-tile` in both Python and JS extractors | **FIXED** |
| Save % misread as `$` | 2026-01-05 | Ignore savings/% nodes, use blob inference to override | **FIXED** |
| Promotional carousel pollution + absurd prices | 2026-01-05 | DOM-scoped extraction, $10k was-price ceiling, $5k savings delta ceiling | **FIXED** |

**Critical Observation:** These fixes are in the codebase but may not be deployed to production workers.

---

## 2. Comparison Summary: Gloorbot vs CheapSkater

| Aspect | Gloorbot (5-Strategy) | CheapSkater (3-Selector) |
|--------|---------------------|---------------------|
| **Selectors** | 5 strategies (data-testid, canonical, aria-label, strikethrough, blob) | 3 selectors (data-testid only) |
| **Code Complexity** | ~330 lines of extraction logic | ~50 lines of extraction logic |
| **Fallback Chain** | Yes (5 strategies in sequence) | No (single attempt) |
| **Inference Risk** | High (blob inference can misinterpret `$` values) | None (no inference) |
| **Diagnostic Support** | Built-in (JSONL traces when enabled) | N/A (not needed) |
| **Tile Group Handling** | Split by `data-tile` (Python) + JS extractor | N/A (no tile groups) |
| **Validation Rules** | Aggressive (9+ rejection criteria) | Minimal (basic price parsing) |
| **Test Coverage** | 4 deterministic tests | N/A (production is test) |

**Key Insight:** CheapSkater's simplicity is its strength. Gloorbot's complexity is its weakness.

---

## 3. Recommended Fix Strategy

### Option A: Simplify to 3-Selector Approach (RECOMMENDED)

**Overview:** Remove strategies 2-5 and adopt CheapSkater's proven 3-selector approach.

#### 3A.1 Changes Required

**File:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py)

**In [`extract_prices_from_card()`](PARALLEL/scraper.py:403-732):**

1. **Keep Strategy 1 (data-testid):** No changes needed - this is the primary strategy
2. **Remove Strategy 2 (canonical selectors):** Delete lines 505-580
3. **Remove Strategy 3 (aria-label scan):** Delete lines 582-630
4. **Remove Strategy 4 (strikethrough):** Delete lines 632-664
5. **Remove Strategy 5 (blob inference):** Delete lines 666-713

**In [`scrape_category_page()`](PARALLEL/scraper.py:1190-1880):**

1. **Remove tile group splitting logic:** The JS extractor already handles `data-tile` splitting correctly (lines 1317-1591)
2. **Keep Python tile group helper:** The [`extract_tile_group_products()`](PARALLEL/scraper.py:735-805) function is still needed for Python-side extraction

**File:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py)

**In [`_deal_from_product()`](apps/worker/src/gloorbot_worker/slot_worker.py:249-414):**

1. **Remove aggressive validation:** Delete lines 264-363 (high-ticket tiny price, non-discounted, extreme pct, absurd was-price, absurd savings)
2. **Keep basic validation:** Lines 249-263 (financing noise, missing prices, invalid prices) are sufficient
3. **Adjust DEAL_THRESHOLD:** Line 28 already reads `DEAL_THRESHOLD` from env

#### 3A.2 Trade-offs

| Pro | Con |
|-----|------|
| **Simplicity** | Easier to understand, debug, and maintain |
| **Reliability** | Matches CheapSkater's proven approach |
| **Edge Case Coverage** | May lose some edge cases (e.g., products without data-testid) |
| **Code Reduction** | Removes ~150 lines from scraper.py |
| **Performance** | Faster extraction (no fallback chain) |
| **Test Impact** | Existing tests may need updates (but they're deterministic) |

#### 3A.3 Implementation Steps

**Step 1: Enable diagnostic logging in worker**
```bash
# Set environment variables in worker startup or supervisor config
export GLOORBOT_PRICE_DIAGNOSTICS=1
export GLOORBOT_DEAL_DIAGNOSTICS=1
```

**Step 2: Run production with diagnostics for 24-48 hours**
- Collect diagnostic JSONL logs from `logs/price_diagnostics/slot_*.jsonl`
- Analyze which strategies are actually failing
- Identify patterns in wrong-price deals

**Step 3: Apply code changes from Option A**
- Commit changes to [`PARALLEL/scraper.py`](PARALLEL/scraper.py)
- Test locally with [`verification/run_suite.py`](verification/run_suite.py)
- Update regression tests if needed

**Step 4: Deploy to production**
- Build new worker installer with updated code
- Update coordinator `WORKER_DOWNLOAD_URL` to point to new installer
- Deploy coordinator to Render
- Monitor for 24-48 hours

**Step 5: Analyze diagnostic data**
- Review diagnostic logs to confirm fix effectiveness
- If issues persist, iterate with Option B

---

### Option B: Keep 5-Strategy System with Diagnostics (ALTERNATIVE)

**Overview:** Maintain current 5-strategy system but enable comprehensive diagnostic logging to identify actual failures.

#### 3B.1 Changes Required

**File:** [`PARALLEL/scraper.py`](PARALLEL/scraper.py)

No code changes needed - diagnostic infrastructure already exists.

**File:** [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py)

**In [`_enable_price_diagnostics_for_slot()`](apps/worker/src/gloorbot_worker/slot_worker.py:160-174):**

1. **Enable by default:** Remove the early return on line 165
2. **Add environment variable check:** Read `GLOORBOT_PRICE_DIAGNOSTICS` and enable if set

#### 3B.2 Trade-offs

| Pro | Con |
|-----|------|
| **Preserves Edge Cases** | Keeps all 5 strategies for rare DOM variations |
| **No Code Changes** | Minimal risk to existing functionality |
| **Diagnostic Visibility** | Full visibility into which strategy succeeds/fails per card |
| **Test Impact** | No changes to existing tests |

#### 3B.3 Implementation Steps

**Step 1: Enable diagnostic logging in worker**
```bash
# Set environment variables in worker startup or supervisor config
export GLOORBOT_PRICE_DIAGNOSTICS=1
export GLOORBOT_DEAL_DIAGNOSTICS=1
```

**Step 2: Run production with diagnostics for 24-48 hours**
- Collect diagnostic JSONL logs from `logs/price_diagnostics/slot_*.jsonl`
- Analyze which strategies are actually failing
- Identify patterns in wrong-price deals

**Step 3: Analyze diagnostic data**
- Build summary statistics: which strategies succeed most often?
- Identify specific DOM patterns causing failures
- Create targeted fixes based on data

**Step 4: Apply targeted fixes**
- Adjust selector priority based on diagnostic data
- Add new regression tests for discovered edge cases
- Update validation rules if needed

**Step 5: Iterate until stable**
- Continue monitoring and adjusting based on production data
- Only remove strategies that consistently fail

---

## 4. Immediate Action Items (Priority Order)

### Priority 1: Enable Diagnostic Logging (CRITICAL - BLOCKER)

**Status:** ❌ NOT DONE

**Why Critical:** We cannot fix what we cannot see. Diagnostic logging is the only way to understand production failures.

**Action:**
1. Set environment variables in worker environment:
   ```bash
   export GLOORBOT_PRICE_DIAGNOSTICS=1
   export GLOORBOT_DEAL_DIAGNOSTICS=1
   ```

2. Or update worker startup code to enable diagnostics by default

**Expected Outcome:** Per-card JSONL traces showing:
- Which strategy succeeded for each card
- All selectors attempted and their counts
- Raw aria-label and text content (truncated)
- Rejection reasons for each candidate

### Priority 2: Verify Worker Version

**Status:** ❌ NOT DONE

**Action:**
1. Check worker version at `C:\Users\User\AppData\Local\GloorbotWorker`
2. Compare with latest code in [`PARALLEL/scraper.py`](PARALLEL/scraper.py)
3. Confirm worker has fixes for:
   - Financing noise filtering (lines 197-246 in scraper.py)
   - Tile group splitting (lines 735-805 in scraper.py)
   - Promotional carousel exclusion (lines 1296-1455 in scraper.py)

**Expected Outcome:** Confirmed worker is running latest code with all fixes applied.

### Priority 3: Run Diagnostic Smoke Test

**Status:** ❌ NOT DONE

**Action:**
1. Run [`verification/live_smoke_lowes.py`](verification/live_smoke_lowes.py) with diagnostics enabled:
   ```bash
   $env:GLOORBOT_LIVE_TEST = "1"
   $env:GLOORBOT_LIVE_HEADLESS = "0"
   python verification/live_smoke_lowes.py
   ```

2. Review diagnostic artifacts in `verification/.artifacts/`
3. Compare scraper-extracted prices with DOM truth prices

**Expected Outcome:** Live validation of price extraction on actual Lowe's pages with diagnostic traces.

### Priority 4: Review Production Data

**Status:** ❌ NOT DONE

**Action:**
1. Query coordinator `/api/v1/status` for recent wrong-price deals
2. Analyze patterns in wrong prices:
   - Are they consistently low ($10, $125, $131)?
   - Do they correlate with specific categories?
   - Are they from specific stores?
3. Identify if issues correlate with:
   - Specific DOM layouts
   - Specific product types
   - Browser versions

**Expected Outcome:** Data-driven understanding of production failure patterns.

### Priority 5: Choose Fix Strategy

**Status:** ❌ NOT DONE

**Action:**
1. After completing Priority 1-4, analyze diagnostic data
2. Choose Option A (simplify) or Option B (diagnose) based on findings
3. Document decision rationale

**Expected Outcome:** Clear path forward with chosen strategy.

---

## 5. Testing Strategy

### 5.1 Pre-Implementation Validation

**Current State:**
- [`verification/run_suite.py`](verification/run_suite.py) has 4 deterministic tests
- All tests pass (100% success rate)

**Tests Cover:**
1. **Tile group splitting:** [`test_tile_group_extraction.py`](verification/run_suite.py:42-43) - Python path
2. **Tile group splitting (JS):** [`test_near_me_dom_tile_group_split.py`](verification/run_suite.py:46-47) - JS near-me path
3. **Financing noise rejection:** [`test_price_extraction_financing_noise.py`](verification/run_suite.py:50-52) - Python extraction
4. **Worker financing rejection:** [`test_worker_price_reject_financing.py`](verification/run_suite.py:55-57) - Worker validation

**Gap:** No live smoke test with diagnostic traces to compare against actual Lowe's DOM.

### 5.2 Post-Implementation Validation

**If Option A (Simplify):**
1. Run [`verification/run_suite.py`](verification/run_suite.py) - all tests should still pass
2. Run [`verification/live_smoke_lowes.py`](verification/live_smoke_lowes.py) with diagnostics
3. Verify diagnostic logs show Strategy 1 (data-testid) succeeding
4. Check for any edge cases lost by removing strategies 2-5

**If Option B (Diagnose):**
1. Run [`verification/run_suite.py`](verification/run_suite.py) - all tests should still pass
2. Run [`verification/live_smoke_lowes.py`](verification/live_smoke_lowes.py) with diagnostics
3. Analyze diagnostic logs to identify failing strategies
4. Create new regression tests for discovered edge cases
5. Verify targeted fixes resolve issues

### 5.3 Regression Test Coverage

**Add tests for:**
- Products without data-testid attributes (if Option A removes fallbacks)
- Products with multiple price nodes (ambiguous which is correct)
- Products with aria-label but no explicit price (edge case for Strategy 3)
- Products in promotional sections (edge case for DOM scoping)

---

## 6. Deployment Considerations

### 6.1 Worker Installer Versioning

**Current State:**
- Latest worker installer: `v0.11.4` (from AGENTS.md milestone 2026-01-05)
- Contains: DOM scoping fixes, tile group fixes

**Deployment Steps:**
1. Create new installer version after code changes
2. Update Git tag (e.g., `v0.12.0`)
3. Build installer with Inno Setup
4. Upload to GitHub Releases
5. Update coordinator `WORKER_DOWNLOAD_URL` environment variable

**Rollback Plan:** Keep previous installer available at fallback URL.

### 6.2 Coordinator Deployment

**Current State:**
- Coordinator deployed to Render from this repo
- Health endpoint: `https://gloorbot-coordinator.onrender.com/healthz`
- Status endpoint: `https://gloorbot-coordinator.onrender.com/api/v1/status`

**Deployment Steps:**
1. Commit code changes to main branch
2. Push to GitHub
3. Render auto-deploys from main branch
4. Verify deployment via health endpoint

**Rollback Plan:** If issues detected within 24 hours, revert to previous commit and redeploy.

### 6.3 CheapSkater Coordination

**Impact:** None - CheapSkater is separate service

**Consideration:** Gloorbot price extraction changes do not affect CheapSkater since it uses its own scraper.

---

## 7. Risk Assessment

### 7.1 Option A (Simplify) Risks

| Risk | Likelihood | Impact | Mitigation |
|-------|------------|--------|------------|
| **Lost edge case coverage** | Medium | Some products may lack data-testid attributes | Add regression tests for discovered cases |
| **Reduced flexibility** | Low | DOM changes could break edge cases | Monitor production closely |
| **Test updates needed** | Medium | Existing tests may need adjustment | Update tests after deployment |
| **Deployment risk** | Low | Code removal is straightforward | Deploy to staging first |

### 7.2 Option B (Diagnose) Risks

| Risk | Likelihood | Impact | Mitigation |
|-------|------------|--------|------------|
| **No code changes** | Low | Minimal risk to existing functionality | None |
| **Diagnostic overhead** | Low | JSONL logging is lightweight | Monitor disk space |
| **Analysis time** | Medium | Requires  collect and analyze data | Set 48-hour diagnostic window |
| **Delayed fix** | Medium | Cannot fix until data collected | Acceptable - diagnostic is blocker |

### 7.3 Shared Risks

| Risk | Likelihood | Impact | Mitigation |
|-------|------------|--------|------------|
| **Worker version mismatch** | High | Production running old code without fixes | Verify version before deployment |
| **Diagnostic logs not enabled** | High | Flying blind without visibility | Enable diagnostics immediately |
| **Production data corruption** | Low | Wrong prices in database | Use CheapSkater cleanup endpoint |

---

## 8. Rollback Plan

### 8.1 Immediate Rollback Triggers

Rollback to previous state if:

1. **New wrong-price patterns emerge** after deployment (e.g., prices consistently 10% lower)
2. **Deal volume drops significantly** (e.g., from 100/day to 10/day)
3. **Worker crashes increase** (e.g., timeout errors)
4. **Coordinator errors spike** (e.g., 500 errors on `/api/v1/deals/bulk`)

### 8.2 Rollback Procedure

**Step 1: Identify issue**
- Check coordinator `/api/v1/status` for error spikes
- Review worker diagnostic logs for patterns
- Confirm issue correlates with deployment

**Step 2: Revert code changes**
```bash
git revert <commit-hash>
git push origin main
```

**Step 3: Redeploy previous version**
```bash
# Update coordinator WORKER_DOWNLOAD_URL to previous installer
# Render will auto-deploy from main branch
```

**Step 4: Verify rollback**
- Check health endpoint
- Monitor deal volume for 24 hours
- Confirm wrong-price patterns stop

### 8.3 Rollback Decision Criteria

| Condition | Action |
|------------|--------|
| Wrong prices increase > 20% | Rollback immediately |
| Deal volume drops > 50% | Rollback immediately |
| Worker crash rate > 10% | Rollback immediately |
| Coordinator error rate > 5% | Rollback immediately |
| Issue persists > 48 hours | Accept and continue with Option B |

---

## 9. Monitoring Strategy

### 9.1 Key Metrics to Track

**Coordinator Metrics:**
- `/api/v1/status` - Check every 5 minutes for:
  - `cheapskater_ingest_url_configured`
  - `forward_status_code` distribution (should be 200)
  - `forward_error` rate (should be null)
  - Recent deal volume

**Worker Metrics:**
- Diagnostic log analysis:
  - Strategy success rate per strategy
  - Most common rejection reasons
  - Cards with no valid price found
- Deal acceptance rate:
  - Total deals submitted
  - Deals rejected by validation
  - Deals rejected by threshold

**CheapSkater Metrics:**
- `/api/ingest/health` - Check every 5 minutes
- Wrong price reports from users

### 9.2 Alert Thresholds

| Metric | Warning Threshold | Critical Threshold |
|----------|-----------------|------------------|
| Wrong price rate > 5% | Investigate within 1 hour | Rollback if > 20% |
| Deal rejection rate > 30% | Investigate within 1 hour | Rollback if > 50% |
| Coordinator error rate > 1% | Investigate within 30 minutes | Rollback if > 5% |
| Worker crash rate > 5% | Investigate within 1 hour | Rollback if > 10% |

### 9.3 Diagnostic Log Analysis

**Weekly Review:**
1. Aggregate diagnostic JSONL logs from all slots
2. Generate summary statistics:
   - Which strategy succeeds most often?
   - Which selectors are never found?
   - Most common rejection reasons
3. Identify trends and patterns
4. Recommend targeted fixes

**Daily Review:**
1. Check recent diagnostic logs for anomalies
2. Verify worker version matches deployed code
3. Validate DEAL_THRESHOLD is correct

---

## 10. Success Criteria

### 10.1 Fix Validation

- [ ] All Priority 1-5 immediate actions completed
- [ ] Diagnostic logging enabled in production
- [ ] Worker version verified as latest
- [ ] Diagnostic smoke test completed with positive results
- [ ] Production data reviewed and patterns identified

### 10.2 Stability Criteria

- [ ] Wrong price rate < 2% for 7 consecutive days
- [ ] Deal volume stable (±10% day-over-day)
- [ ] Worker crash rate < 1%
- [ ] Coordinator error rate < 0.5%
- [ ] User reports of wrong prices < 1 per week

### 10.3 Long-term Criteria

- [ ] No new wrong-price patterns emerge for 30 days
- [ ] Diagnostic overhead acceptable (< 5% CPU/memory)
- [ ] Team confident in price extraction reliability
- [ ] Documentation updated with lessons learned

---

## Appendix A: Code References

### Key Files

| File | Purpose | Lines of Interest |
|-------|---------|-------------------|
| [`PARALLEL/scraper.py`](PARALLEL/scraper.py) | Main scraper with 5-strategy price extraction | 403-732 (extraction logic) |
| [`apps/worker/src/gloorbot_worker/slot_worker.py`](apps/worker/src/gloorbot_worker/slot_worker.py) | Worker with validation and diagnostics | 249-414 (deal validation) |
| [`verification/run_suite.py`](verification/run_suite.py) | Deterministic regression tests | 1-78 |
| [`verification/live_smoke_lowes.py`](verification/live_smoke_lowes.py) | Live smoke test with diagnostics | N/A |
| [`agents.md`](agents.md) | Project coordination and milestones | N/A |

### Key Functions

| Function | Location | Purpose |
|----------|---------|---------|
| [`extract_prices_from_card()`](PARALLEL/scraper.py:403) | Scraper price extraction with 5 strategies | 403-732 |
| [`extract_tile_group_products()`](PARALLEL/scraper.py:735) | Split tile_group by data-tile | 735-805 |
| [`_deal_from_product()`](apps/worker/src/gloorbot_worker/slot_worker.py:249) | Worker deal validation | 249-414 |
| [`_enable_price_diagnostics_for_slot()`](apps/worker/src/gloorbot_worker/slot_worker.py:160) | Enable per-slot diagnostics | 160-174 |

---

## Appendix B: Decision Matrix

### Option A vs Option B Comparison

| Factor | Option A (Simplify) | Option B (Diagnose) |
|---------|---------------------|-------------------|
| **Implementation effort** | 2-5 days | 5-10 days (data collection + analysis) |
| **Code changes** | ~150 lines removed | 0 lines added |
| **Risk** | Medium (lost edge cases) | Low (no code changes) |
| **Time to fix** | Fast (once deployed) | Slow (need data first) |
| **Long-term maintenance** | Simpler (3 selectors) | Complexer (5 strategies + diagnostics) |
| **Diagnostic visibility** | Low (only Strategy 1 visible) | High (all 5 strategies visible) |
| **Test updates needed** | Maybe (edge cases lost) | Yes (new tests for discovered issues) |
| **Recommended for** | Production stability, known-good approach | Production investigation phase |

**Recommendation:** Start with **Option B (Diagnose)** to understand the actual problem, then transition to **Option A (Simplify)** once root cause is identified.

---

## Appendix C: Implementation Checklist (Option A)

### Phase 1: Preparation (1-2 days)
- [ ] Enable diagnostic logging in worker environment
- [ ] Verify worker version matches latest code
- [ ] Run diagnostic smoke test to establish baseline
- [ ] Review existing regression tests

### Phase 2: Code Changes (2-3 days)
- [ ] Remove Strategy 2 (canonical selectors) from scraper.py
- [ ] Remove Strategy 3 (aria-label scan) from scraper.py
- [ ] Remove Strategy 4 (strikethrough) from scraper.py
- [ ] Remove Strategy 5 (blob inference) from scraper.py
- [ ] Update regression tests if needed
- [ ] Run verification suite to confirm no regressions

### Phase 3: Testing (1-2 days)
- [ ] Run verification/run_suite.py (all tests pass)
- [ ] Run verification/live_smoke_lowes.py with diagnostics
- [ ] Analyze diagnostic results
- [ ] Create new regression tests for discovered edge cases

### Phase 4: Deployment (1-2 days)
- [ ] Build new worker installer
- [ ] Update coordinator WORKER_DOWNLOAD_URL
- [ ] Deploy coordinator to Render
- [ ] Deploy to staging environment first (if available)
- [ ] Monitor for 24 hours before full production rollout

### Phase 5: Validation (7 days)
- [ ] Monitor wrong price rate
- [ ] Monitor deal volume
- [ ] Monitor worker crash rate
- [ ] Monitor coordinator error rate
- [ ] Review diagnostic logs weekly
- [ ] Collect user feedback on wrong prices

### Phase 6: Stabilization (14 days)
- [ ] Analyze 30 days of diagnostic data
- [ ] Apply targeted fixes based on findings
- [ ] Update regression tests
- [ ] Consider transitioning to Option A if Option B shows consistent failures
- [ ] Update documentation with lessons learned

---

**Document Status:** COMPLETE - Ready for implementation planning
