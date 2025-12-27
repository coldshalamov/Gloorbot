# Local Testing Guide for Lowe's Apify Actor

## Quick Start

### 1. Install Dependencies

```bash
cd lowes-apify-actor
pip install -r requirements.txt
playwright install chrome
```

### 2. Run the Test

```bash
python test_local.py
```

The test will:
- Launch a visible Chrome browser (headless=False)
- Test anti-fingerprinting measures
- Check for Akamai blocks
- Test pickup filter functionality on 2 categories
- Extract products from up to 3 pages per category
- Generate a detailed report in `TEST_RESULTS_LOCAL.md`

### 3. What to Watch For

**During the test, you'll see:**
- Chrome browser open (not headless)
- Navigation to Lowe's homepage
- Category pages loading
- Pickup filter being clicked
- Product grids appearing

**Expected Duration:** 5-10 minutes total

**Signs of Success:**
- ✅ Browser launches without errors
- ✅ Lowe's homepage loads (not Access Denied)
- ✅ Pickup filter buttons are found and clicked
- ✅ Products are extracted from pages
- ✅ No "Access Denied" or Reference # errors

**Signs of Failure:**
- ❌ "Access Denied" page appears
- ❌ "Reference #" error appears (Akamai block)
- ❌ Pickup filter selector not found
- ❌ No products extracted
- ❌ Browser crashes or hangs

## Test Configuration

The test is configured via environment variables (set in `test_local.py`):

```python
CHEAPSKATER_DIAGNOSTICS=1        # Enable verbose logging
CHEAPSKATER_TEST_MODE=1          # Limit to 2 pages per category
CHEAPSKATER_PICKUP_FILTER=1      # Enable pickup filter clicks
CHEAPSKATER_FINGERPRINT_INJECTION=1  # Enable anti-fingerprinting
CHEAPSKATER_BROWSER_CHANNEL=chrome   # Use real Chrome (not Chromium)
```

## What's Being Tested

### Test 1: Browser Launch
- Can we launch Chrome with anti-fingerprinting?
- Do stealth measures apply correctly?
- Does fingerprint randomization work?

### Test 2: Akamai Block Check
- Does Akamai block us immediately?
- Can we pass the challenge page?
- Do we get "Access Denied"?

### Test 3: Fingerprint Uniqueness
- Is our fingerprint realistic?
- Are screen dimensions randomized?
- Is WebGL vendor/renderer spoofed?

### Test 4: Pickup Filter (per category)
- Can we find the pickup filter UI element?
- Does clicking it actually apply the filter?
- Does the URL change or product count decrease?

### Test 5: Product Extraction (per category)
- Can we extract products from the DOM?
- Are prices, titles, SKUs captured?
- Is JSON-LD parsing working?

### Test 6: Full Scrape (per category)
- Can we paginate through 2-3 pages?
- Do products accumulate correctly?
- Does smart pagination work?

## Troubleshooting

### If Akamai Blocks You Immediately

**Try enabling playwright-stealth enhancements:**
```python
# In test_local.py, uncomment these:
os.environ["CHEAPSKATER_RANDOM_UA"] = "1"
os.environ["CHEAPSKATER_RANDOM_TZLOCALE"] = "1"
```

**Or add a proxy:**
```python
os.environ["CHEAPSKATER_PROXY"] = "http://your-proxy:port"
```

### If Pickup Filter Fails

Check the console output for:
- Which selectors were tried
- How many elements matched each selector
- What text was found in the elements

The test enables full diagnostics, so you'll see detailed logs.

### If No Products Found

This could mean:
1. Pickup filter didn't actually apply (check URL for `pickup` or `availability` params)
2. Store doesn't have items available for pickup
3. Selectors changed (check page HTML)

## Test Output

### Console Output
- Real-time test results
- Detailed logs from the actor
- Selector match counts
- Product extraction details

### TEST_RESULTS_LOCAL.md
- Summary of all tests
- Pass/fail status
- Detailed metrics
- Sample products extracted
- Error messages and stack traces

## Next Steps

### If All Tests Pass
✅ Actor is ready for deployment to Apify
✅ Pickup filter is working
✅ Anti-fingerprinting is effective
✅ Product extraction is successful

### If Tests Fail
❌ Review TEST_RESULTS_LOCAL.md for details
❌ Check which specific tests failed
❌ Look at error messages and URLs
❌ Consider adding proxies or adjusting stealth measures

## Advanced Testing

### Test with Proxies

Set a proxy before running:
```bash
export CHEAPSKATER_PROXY="http://username:password@proxy-host:port"
python test_local.py
```

### Test with Different Categories

Edit `test_local.py` and modify the `categories` list:
```python
categories = [
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
    {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    # Add more...
]
```

### Enable More Diagnostics

```python
os.environ["CHEAPSKATER_DIAGNOSTICS_AUDIO"] = "1"  # Include audio fingerprint
os.environ["CHEAPSKATER_DIAGNOSTICS_DRIFT"] = "1"  # Check fingerprint drift
os.environ["CHEAPSKATER_DEBUG_BLOCKING"] = "1"     # Log resource blocking
```

## Known Issues

1. **First run may be slow** - Playwright needs to download Chrome
2. **Akamai may block on first attempt** - This is expected without proxies
3. **Some categories may have no pickup items** - This is normal
4. **Rate limiting** - Lowe's may rate limit after many requests

## Success Criteria

For the actor to be deployment-ready:
- [ ] Browser launches successfully
- [ ] No immediate Akamai blocks
- [ ] Pickup filter applies on at least 1 category
- [ ] At least 1 product extracted
- [ ] No crashes or fatal errors
