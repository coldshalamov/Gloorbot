# Local Scraper Testing Guide

**PROBLEM:** The full rebuild → deploy → test cycle takes HOURS and is painful for debugging.

**SOLUTION:** Test scraper changes locally in MINUTES before deploying.

---

## Quick Testing Workflow

### 1. Test Pickup Filter Logic (FASTEST - 2-5 minutes)

Tests ONLY the pickup filter disabled detection:

```bash
cd PARALLEL
python test_pickup_filter.py
```

**What it does:**
- Opens browser (you can watch)
- Tests 10 categories at one store
- Shows which filters are enabled vs disabled
- Verifies your fix is working

**Use this when:**
- Testing the pickup filter disabled detection fix
- Verifying filter logic changes
- Quick sanity check before full test

---

### 2. Test Full Category Scrape (MEDIUM - 5-15 minutes)

Tests one complete category scrape:

```bash
cd PARALLEL
python test_scraper_local.py
```

**What it does:**
- Full warmup + store setup
- Scrapes one category completely
- Shows all products found
- Reports markdown counts
- You can watch browser behavior

**Use this when:**
- Testing price extraction logic
- Verifying pagination works
- Checking product data quality
- Testing new selector changes

---

### 3. Customize the Test

Edit the test files to change what gets tested:

**Test different store:**
```python
# In test_scraper_local.py or test_pickup_filter.py, change:
test_store = all_stores[0]  # First store
test_store = all_stores[5]  # Sixth store
```

**Test specific category:**
```python
# Pick a category that likely has deals:
test_category = "https://www.lowes.com/pl/Generators--Electrical/..."
```

**Test more/fewer categories:**
```python
# In test_pickup_filter.py:
for i, category_url in enumerate(all_categories[:10], 1):  # Change 10 to whatever
```

---

## When to Rebuild the Worker

**DON'T rebuild for:**
- Price extraction tweaks (test with `test_scraper_local.py`)
- Filter logic changes (test with `test_pickup_filter.py`)
- Selector adjustments
- Debugging/experimenting

**DO rebuild when:**
- You've tested locally and verified the fix works
- You're ready to deploy to production
- You've made multiple related fixes and want to deploy them all

---

## Workflow Example

### Debugging Price Extraction:

1. **Make changes** to `scraper.py` price extraction logic
2. **Test locally:** `python test_scraper_local.py`
3. **Watch browser** - see if prices are correct
4. **Iterate quickly** - make more changes, re-run test
5. **Once working** - push to GitHub and rebuild worker

**Time saved:** Instead of 4-6 hours per iteration, you get feedback in 5-10 minutes!

---

## Tips

- **Keep browser visible** (`headless=False`) so you can see what's happening
- **Use breakpoints** - add `import pdb; pdb.set_trace()` to pause execution
- **Test edge cases** - pick categories that are likely to have disabled filters or unusual prices
- **Check logs** - test scripts print detailed output to help debug

---

## Requirements

Same as the main scraper:
- Python 3.8+
- Playwright installed: `pip install playwright`
- Chrome installed via Playwright: `playwright install chrome`
- `urls.txt` file in the PARALLEL folder

---

## Next Steps After Local Testing

Once your local tests pass:

1. **Commit changes:**
   ```bash
   git add PARALLEL/scraper.py
   git commit -m "Fix: Detect disabled pickup filters to skip empty categories"
   git push
   ```

2. **Rebuild worker:**
   - Go to GitHub Actions
   - Run "Build Worker Installer"
   - Wait for build (5-10 min)

3. **Deploy:**
   - Download new `WorkerSetup.exe`
   - Uninstall old worker
   - Install new worker
   - Let it run overnight

4. **Verify in production:**
   - Check logs for "DISABLED" messages
   - Verify it's skipping empty categories
   - Confirm no bad data on cheapskater site
