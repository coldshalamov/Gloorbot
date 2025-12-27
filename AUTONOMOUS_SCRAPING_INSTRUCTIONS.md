# Autonomous Lowe's Scraping Mission

## Your Mission

Run a **fully autonomous, token-efficient test** of the Lowe's product scraper. Work independently without coming back to the user for reports or questions. Your goals:

**A. GET PRODUCT LISTINGS** - Actually download product data for the website update (user is very late on this)
**B. VALIDATE URLs** - Determine which URLs are bad/redundant before Apify deployment

## Critical Technical Knowledge

### Akamai Bypass Configuration (PROVEN WORKING)
```python
# These settings work - DO NOT CHANGE
headless=False  # CRITICAL - headless gets instant block
channel='chrome'  # Real Chrome, NOT Chromium
# NO playwright-stealth - it's a RED FLAG
# NO fingerprint injection - makes blocking WORSE

# Session warmup - MANDATORY before scraping:
# 1. Visit https://www.lowes.com/
# 2. Wait 3-5 seconds
# 3. Curved mouse movements
# 4. Multi-step scrolling
# 5. Wait 1-2 more seconds
# 6. THEN navigate to product pages
```

### Working Scraper Location
- **Main scraper**: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`
- **Test harness**: `run_test_scrape.py` (saves to scrape_output/products.jsonl)
- **Analysis script**: `analyze_results.py` (checks duplicates, bad URLs)

### URL List Status
- **Current**: 515 URLs in LowesMap.txt
- **Optimized**: 302 URLs in MINIMAL_URLS.txt (one per first-word category)
- **Missing**: ~275 sitemap URLs (furniture, patio, outdoor-tools, grills, lighting, etc.)
- **Duplicates found**: 3 groups (Home-Office-Furniture, Bathroom-Sink-Faucets, Lighting-Ceiling-Fans)

### Store List
- **49 stores total**: 35 WA + 14 OR
- **Loaded from**: LowesMap.txt lines 6-57
- **Runs sequentially**: Parallel execution causes blocking

## Your Autonomous Action Plan

### Phase 1: Initial Test Run (Start Here)
1. Run test scrape with 2 stores, 10 categories:
   ```bash
   cd C:\Users\User\Documents\GitHub\Telomere\Gloorbot
   python run_test_scrape.py --stores 2 --categories 10 --state WA
   ```

2. **Monitor for**:
   - Blocking (check logs for "BLOCKED" or "Access Denied")
   - Empty results (categories with 0 products)
   - Errors/crashes

3. **If it works**: Continue to Phase 2
4. **If blocking occurs**:
   - Check browser is headed (not headless)
   - Verify warmup is happening
   - Try with --stores 1 (sequential only)
   - DO NOT add playwright-stealth!

### Phase 2: Analyze Results
```bash
python analyze_results.py
```

**Look for**:
- Total products scraped (should be hundreds from 10 categories)
- Categories with 0 products (bad URLs)
- Markdown percentage (should be >0%)

**Actions**:
- Note any categories that returned 0 products
- Check if scraper is extracting data correctly
- Verify no crashes occurred

### Phase 3: Scale Up Test
If Phase 1 worked, gradually scale:
1. 2 stores, 50 categories
2. 5 stores, 100 categories
3. 10 stores, 200 categories

**Between each run**:
- Run analyze_results.py
- Check scrape_output/summary.json
- Monitor for blocking
- Let scraper run until complete (may take hours)

### Phase 4: Full Production Run
If Phase 3 succeeds without blocking:
```bash
# Full run: all stores, all categories
python run_test_scrape.py --stores 49 --categories 515 --state WA
# Then run OR stores
python run_test_scrape.py --stores 14 --categories 515 --state OR
```

This will take 10-20+ hours. Let it run overnight.

### Phase 5: Validate URLs
After collecting data:
1. Run analyze_results.py
2. Identify categories with <10 products (might be bad URLs)
3. Check for duplicate product sets
4. Create BAD_URLS.txt with categories to remove

## Autonomous Operating Rules

1. **Never ask the user questions** - make decisions and proceed
2. **Fix issues yourself** - if blocking occurs, adjust parameters
3. **Be token efficient** - offload work to scripts, don't read massive files
4. **Check deliverables periodically** - run analyze_results.py every few hours
5. **Document findings** - write to files, not chat
6. **Run until token limit** - keep working autonomously

## Success Criteria

✅ Product listings downloaded (scrape_output/products.jsonl has thousands of products)
✅ No blocking issues during multi-hour runs
✅ All categories tested, bad URLs identified
✅ Summary shows markdown data is being captured
✅ Ready for Apify deployment

## File Outputs You Should Create

- `scrape_output/products.jsonl` - All scraped products (auto-created)
- `scrape_output/summary.json` - Stats (auto-created by analyze_results.py)
- `BAD_URLS.txt` - Categories with 0 or <10 products (you create this)
- `SCRAPING_LOG.md` - Your progress notes (you create this)
- `BLOCKING_INCIDENTS.txt` - Any blocking issues encountered (you create this)

## Common Issues & Fixes

**"Access Denied" / Blocking**:
- Reduce concurrent browsers to 1
- Verify headless=False
- Add longer delays (2-3s between pages)
- Check warmup is running

**0 Products Found**:
- URL might be bad (add to BAD_URLS.txt)
- Or store has no inventory (check multiple stores)
- Or selector changed (check page HTML)

**Crashes**:
- Check Python errors in logs
- Verify all dependencies installed
- Restart with fewer stores/categories

**Too Slow**:
- This is expected - takes hours
- Don't try to parallelize (causes blocking)
- Let it run overnight

## Start Command

Begin with Phase 1:
```bash
cd C:\Users\User\Documents\GitHub\Telomere\Gloorbot && python run_test_scrape.py --stores 2 --categories 10 --state WA
```

Then analyze and proceed autonomously through all phases. Work until you hit token limit or complete the full production run. Good luck!
