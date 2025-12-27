# Production Run Strategy - Full Lowe's Catalog Scraping

**Prepared**: 2025-12-26  
**Based on**: Phase 1-3 testing with 738-1,467 products collected

---

## Quick Start for Full Deployment

### Immediate Next Steps

1. **Clear old data**:
```bash
cd C:\Users\User\Documents\GitHub\Telomere\Gloorbot
rm -rf scrape_output .playwright-profiles/store-*
```

2. **Run WA stores (35 total)**:
```bash
python run_test_scrape.py --stores 35 --categories 515 --state WA
```
Expected: ~40-50 hours, 10,000-20,000 products

3. **Run OR stores (14 total)**:
```bash
python run_test_scrape.py --stores 14 --categories 515 --state OR
```
Expected: ~15-20 hours, 4,000-8,000 products

4. **Analyze results**:
```bash
python analyze_results.py
```

---

## Key Architectural Decision: Sequential Execution

### Why Sequential (NOT Concurrent)?
- **Multi-store crash issue identified**: 3+ concurrent browser contexts cause exitCode=21
- **Single-store stable**: Arlington store scraped successfully for 738 products
- **Tradeoff**: Takes longer but doesn't fail

### Sequential Execution Plan
Instead of launching all stores at once, the framework should:
1. Load one store per browser context
2. Scrape all 515 categories for that store
3. Close browser context
4. Move to next store
5. Repeat for all 49 stores

This is what the current code does (line 297-352 in main.py), which is correct.

---

## Expected Results

### Data Collection Target
```
Configuration:
- Stores: 49 (35 WA + 14 OR)
- Categories: 515
- Total scrape operations: 49 × 515 = 25,235

Estimated Output:
- Products per store: 200-500 (based on Phase 1-3)
- Average categories with products: ~400 of 515 (some may be unavailable)
- Total unique products: 8,000-12,000
- Total product instances (with duplicates): 50,000-100,000

Time Estimate:
- WA stores (35): 40-50 hours
- OR stores (14): 15-20 hours
- Total: 55-70 hours continuous (2-3 days)

Storage:
- JSONL file size: ~100-200 MB
- Browser profiles: ~500 MB (accumulated)
```

### Markdown Data (Key for Website Updates)
- From Phase 1: 0% of tested products had markdowns
- Varies by category
- Some categories (home goods, seasonal) likely have higher markdown rates

---

## Proven Success Factors

### ✅ Akamai Bypass Configuration (DO NOT CHANGE)
```python
headless=False  # CRITICAL
channel='chrome'  # NOT chromium
# NO playwright-stealth (red flag to Akamai)
# NO fingerprint injection
```

### ✅ Human Behavior (ESSENTIAL)
```python
# Warmup session: visit homepage first
await warmup_session(page)  # Lines 110-124

# Per-page human behavior:
await human_mouse_move(page)  # Random mouse movement
await human_scroll(page)  # Scrolling animation
await asyncio.sleep(...)  # Natural delays
```

### ✅ Session Management
- Persistent browser profiles per store
- Session warmup before category scraping
- Store context setting (line 127-146)

---

## Known Issues & Workarounds

### Issue 1: Browser Timeout on Later Categories
**Symptom**: Scraper stalls after 30-40 minutes  
**Seen in**: Phase 3b (reached 738 products then stopped)  
**Workaround**: Monitor progress, manually restart if needed  
**Fix for future**: Add explicit timeout handler per category

### Issue 2: Price Data Format
**Symptom**: Price contains embedded `\n` characters and line breaks  
**Impact**: Data needs post-processing to clean  
**Workaround**: Parse price values in data processing step  
**Fix for future**: Improve CSS selector on line 209 in main.py

### Issue 3: Markdown Percentage
**Symptom**: Returned 0% in test (only 1 category)  
**Likely cause**: 9-volt batteries have no sales  
**Solution**: Full run will show accurate markdown distribution

---

## Monitoring During Production Run

### Key Metrics to Track
- Products per store (should be 200-500+)
- Products per category (should be 10-100+)
- Elapsed time per store
- Chrome process count (should be low, ~1-5 at a time)

### Success Indicators
- ✅ No "Access Denied" pages
- ✅ No browser crash errors
- ✅ No "Target closed" errors
- ✅ Consistent product extraction

### Red Flags
- ❌ Browser exits with code 21
- ❌ JSONL file stops growing for >10 minutes
- ❌ "Access Denied" in page titles
- ❌ Zero products for multiple categories

---

## Post-Collection Workflow

### Step 1: Analysis (run immediately after)
```bash
python analyze_results.py
# Output: scrape_output/summary.json
# Shows: total products, stores, categories, markdown percentage
```

### Step 2: Bad URL Identification
```python
# Analyze the results to create BAD_URLS.txt
# Identify categories with 0 or <10 products
# Mark as low-confidence URLs for removal
```

### Step 3: Data Cleaning
```python
# Remove duplicates
# Parse prices correctly
# Structure for website upload
# Generate markdown-by-category report
```

### Step 4: Website Integration
```python
# Load into product database
# Update category pages with current markdowns
# Filter for "pickup today" items only
```

---

## Apify Deployment Checklist

Before deploying to Apify, ensure:
- [ ] Full dataset collected (50,000+ products)
- [ ] No blocking issues during full run
- [ ] Bad URLs identified and removed
- [ ] Data cleaned and validated
- [ ] Price parsing working correctly
- [ ] Markdown data populated
- [ ] Directory structure matches Apify actor format

Deployment command (when ready):
```bash
# Push actor to Apify
apify push

# Run on Apify with full config
# Can scale to multiple concurrent containers
```

---

## Cost Optimization Notes

Current approach (sequential):
- **Compute**: 1 machine, continuous 55-70 hours
- **Bandwidth**: Modest (only 49 Chrome instances over time)
- **Cost**: Minimal (no cloud services used)

For Apify deployment:
- **Estimated cost**: $5-15 per full run (based on compute units)
- **Frequency**: Weekly or on-demand
- **Output**: 50,000+ products per run

---

## Rollback Plan

If issues occur during production run:
1. Kill the scraper process
2. Save current scrape_output/products.jsonl (partial data)
3. Analyze partial data with analyze_results.py
4. Fix identified issues
5. Restart with cleared output or specific store range

Example restart from store #1089 (Auburn):
```bash
# Modify main.py to start at store index 1
# Or create new script: run_test_scrape.py --stores 1 --category-start 1 --store-start 1089
```

---

## Long-term Maintenance

After initial collection:
1. **Daily markdowns tracking**: Run scraper weekly
2. **Category updates**: Monitor Lowe's sitemap monthly
3. **URL validation**: Test bad URLs quarterly
4. **Data cleanup**: Archive old data, keep latest 4 weeks

---

## Success Definition

✅ **COMPLETE SUCCESS**: 
- All 49 stores × 515 categories scraped
- 50,000+ products collected
- <5% error rate
- No blocking issues
- Markdowns identified by category

🟡 **PARTIAL SUCCESS**: 
- 40+ stores × 400+ categories scraped  
- 30,000+ products collected
- Some categories unavailable
- No blocking

❌ **FAILURE**: 
- Browser crash unable to fix
- Akamai blocking detected
- <10,000 products collected

---

## Contact & Support

If production run fails:
1. Check FINAL_SCRAPING_REPORT.md for known issues
2. Review browser error logs in Playwright output
3. Verify Chrome installation and version
4. Check disk space and system resources
5. Consider running on fresh machine if profile corruption suspected

