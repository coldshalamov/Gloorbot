# Next Steps - Lowe's Scraper Testing

## Current Status
- ✅ Test script created and working
- ✅ Browser automation validated
- ✅ Anti-fingerprinting confirmed active
- ❌ **BLOCKED:** Akamai denies category page access without proxy
- ❌ **UNTESTED:** Pickup filter, product extraction, pagination

---

## Immediate Action Required: Add Residential Proxy

### Why You Need a Proxy
The test revealed that Akamai blocks category pages when accessed from a local IP address. The homepage loads fine, but deeper navigation triggers an "Access Denied" error.

**Without proxy:**
```
Access Denied
You don't have permission to access "http://www.lowes.com/pl/The-back-aisle/..." on this server.
Reference #18.23d5dd17.1766709834.1e758c20
```

**With residential proxy:**
- Request appears to come from a home user
- Akamai much less likely to block
- Category pages should load successfully
- Can test pickup filter and product extraction

---

## Option 1: Test with a Proxy (Recommended)

### Step 1: Get Proxy Credentials
Choose a residential proxy provider:

**Budget Options:**
- **Proxy-Cheap:** $5/GB (acceptable quality)
- **IPRoyal:** $7/GB (good quality)

**Premium Options:**
- **Smartproxy:** $12.5/GB (very good)
- **Bright Data:** $15/GB (best quality, lowest block rate)

### Step 2: Configure Proxy in Test
Edit `lowes-apify-actor/test_local.py` and add this line at the top (around line 31):

```python
# Add your proxy here
os.environ["CHEAPSKATER_PROXY"] = "http://username:password@proxy-host:port"
```

Example:
```python
os.environ["CHEAPSKATER_PROXY"] = "http://user123:pass456@residential.proxy-cheap.com:10001"
```

### Step 3: Re-run Test
```bash
cd lowes-apify-actor
python test_local.py
```

### Step 4: Check Results
Look for:
- ✅ Category pages load (no "Access Denied")
- ✅ Pickup filter elements found
- ✅ Pickup filter applied successfully
- ✅ Products extracted (count > 0)
- ✅ Screenshots show actual product grids

---

## Option 2: Test Without Proxy (Workarounds)

If you don't have proxy access yet, try these workarounds:

### Workaround 1: Enable Store Context + Longer Waits

Edit `lowes-apify-actor/test_local.py`:

```python
# Change these lines:
os.environ["CHEAPSKATER_SET_STORE_CONTEXT"] = "1"  # Was "0"
os.environ["CHEAPSKATER_BLOCK_RESOURCES"] = "1"    # Was "0"
```

**Why this might help:**
- Store selection flow builds session legitimacy
- Loading all resources makes behavior more realistic
- Akamai may accept session after seeing normal UI interaction

**Try it:**
```bash
python test_local.py
```

### Workaround 2: Add Manual Delays

Modify `test_local.py` to add longer waits:

In the `test_akamai_block` function, after homepage loads:
```python
# After: await page.goto("https://www.lowes.com/", ...)
# Add:
await asyncio.sleep(10)  # Wait 10 seconds before category navigation
```

**Why this might help:**
- Gives Akamai time to complete fingerprinting
- Allows cookies to fully set
- Reduces "bot rushing" detection signal

### Workaround 3: Try from Different Network

- Try test from home WiFi (if currently on data center/VPN)
- Try from mobile hotspot
- Try from different ISP

**Why this might help:**
- Akamai may whitelist certain ISP ranges
- Residential IPs less likely to be flagged

---

## Option 3: Deploy to Apify and Test There

If you have Apify account with residential proxies configured:

### Step 1: Push to Apify
```bash
cd lowes-apify-actor
apify push
```

### Step 2: Configure Input
In Apify Console, use this minimal test input:
```json
{
  "stores": [
    {
      "store_id": "0004",
      "name": "Seattle Rainier",
      "zip": "98144"
    }
  ],
  "categories": [
    {
      "name": "Clearance",
      "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"
    }
  ],
  "max_pages_per_category": 3
}
```

### Step 3: Enable Proxy in Apify
In Actor settings:
- Enable "Use Apify Proxy"
- Select "Residential" proxy group
- Country: US

### Step 4: Run and Check Results
Look in Apify logs for:
- Did category pages load?
- Was pickup filter applied?
- Were products extracted?

---

## What to Look For in Next Test

### Success Indicators ✅
1. **Category page loads:**
   ```
   [Clearance] Page title: The Back Aisle at Lowes.com
   ```
   (NOT "Access Denied")

2. **Pickup filter found:**
   ```
   [Clearance] Pickup selector counts: [('label:has-text("Get It Today")', 5), ...]
   ```

3. **Pickup filter applied:**
   ```
   [Clearance] Clicking pickup filter: 'Get It Today'
   [Clearance] Pickup filter VERIFIED via element-state
   ```

4. **Products extracted:**
   ```
   [Clearance] Found 24 (total: 24)
   ```

5. **Test results:**
   ```
   Total Tests: 8
   Passed: 8
   Failed: 0
   Products Found: 48+
   ```

### Failure Indicators ❌
1. **Still blocked:**
   ```
   Access Denied
   Reference #18.23d5dd17...
   ```

2. **Pickup filter not found:**
   ```
   [Clearance] Pickup filter FAILED after 3 attempts
   ```

3. **No products:**
   ```
   Products Found: 0
   ```

---

## Decision Tree

```
Do you have residential proxy?
├─ YES → Configure in test_local.py → Run test → Analyze results
└─ NO → Do you have Apify account with proxies?
    ├─ YES → Deploy to Apify → Run with test input → Analyze results
    └─ NO → Try workarounds OR get proxy trial
        ├─ Workaround 1: Enable store context
        ├─ Workaround 2: Add manual delays
        └─ Workaround 3: Try different network
```

---

## Expected Timeline

### With Proxy Access
- **Configure proxy:** 5 minutes
- **Run test:** 5-10 minutes
- **Analyze results:** 10 minutes
- **Total:** 20-25 minutes

### With Workarounds
- **Try each workaround:** 10-15 minutes each
- **Multiple attempts:** 30-60 minutes
- **Success rate:** 20-30% (uncertain)

### With Apify Deployment
- **Push to Apify:** 5 minutes
- **Configure:** 5 minutes
- **Run test:** 10-15 minutes
- **Total:** 20-25 minutes

---

## After Successful Test

Once category pages load and pickup filter works, you should see:

### Test Results Summary
```
Total Tests: 8
Passed: 8
Failed: 0
Products Found: 50-100
Akamai Blocks: 0
Pickup Filter Success Rate: 2/2
```

### Next Steps After Success
1. ✅ Review extracted product data quality
2. ✅ Validate SKUs, prices, titles are correct
3. ✅ Check pickup filter actually filtered to "available today" items
4. ✅ Deploy to Apify for production test
5. ✅ Run full multi-store test with all categories
6. ✅ Monitor for Akamai blocks at scale

---

## Contact Information

If you need help:
1. Check screenshots in `lowes-apify-actor/screenshot_*.png`
2. Review `TEST_RESULTS_LOCAL.md` for detailed logs
3. Check console output for error messages
4. Look at `TEST_RESULTS_SUMMARY.md` for analysis

---

## Quick Commands Reference

### Run test:
```bash
cd lowes-apify-actor
python test_local.py
```

### Run test with proxy:
```python
# Edit test_local.py first to add:
os.environ["CHEAPSKATER_PROXY"] = "http://user:pass@host:port"
```
```bash
python test_local.py
```

### View results:
```bash
cat TEST_RESULTS_LOCAL.md
```

### View screenshots:
```bash
ls -la screenshot_*.png
```

### Clean up for fresh test:
```bash
rm screenshot_*.png
rm TEST_RESULTS_LOCAL.md
```

---

## Summary

**Current blocker:** Akamai blocks category pages without residential proxy

**Solution:** Add residential proxy to test configuration

**Alternative:** Deploy to Apify with residential proxy enabled

**Workarounds:** Enable store context + resource loading, add delays, try different network

**Next action:** Choose Option 1, 2, or 3 above and proceed

**Time estimate:** 20-60 minutes to complete next test iteration
