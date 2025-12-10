# Lowes URL Discovery - Complete Guide

## The Challenge

Lowes.com has **aggressive bot detection** that blocks automated crawlers, even sophisticated ones with:
- Playwright Stealth
- Device emulation
- Human-like delays
- Realistic fingerprints

Your existing scraper code works perfectly for **scraping products** when given URLs, but **discovering new URLs** automatically is blocked.

## What You Currently Have

- **193 URLs** in `catalog/legacy_building_materials.lowes.yml`
- Working anti-blocking infrastructure in your scraper
- `discover_categories()` function that used to work but is now blocked

## Solutions

### Solution 1: Manual-Assisted URL Capture (RECOMMENDED)

**File:** `manual_url_capture.py`

This tool opens a **visible browser** where YOU manually navigate Lowes, and it automatically captures all URLs you encounter.

**How to use:**
```bash
python manual_url_capture.py
```

1. Browser opens at https://www.lowes.com/c/Departments
2. You click through departments manually
3. Script captures all /pl/ and /c/ URLs automatically
4. Press Ctrl+C when done
5. All URLs saved to timestamped files

**Why this works:**
- YOU are browsing (not a bot)
- Real human interaction
- Builds browser history/cookies naturally
- Bypasses all bot detection

**Efficiency tips:**
- Open all department dropdowns
- Right-click interesting links → "Open in new tab"
- The script captures from ALL tabs
- Spend 15-20 minutes clicking around = hundreds of URLs

### Solution 2: Sitemap Extraction

**File:** `extract_from_sitemap.py`

Attempts to extract URLs from Lowes' sitemap.xml files.

```bash
python extract_from_sitemap.py
```

May work if Lowes exposes sitemaps, but likely also blocked.

### Solution 3: Browser DevTools Method (No Code)

1. Open Lowes.com in browser
2. Open DevTools (F12) → Network tab
3. Navigate through departments
4. Filter network requests for `/pl/` and `/c/`
5. Export as HAR file
6. Parse URLs from HAR

### Solution 4: Existing Discovery Code (Currently Blocked)

Your `app/catalog/discover_lowes.py` has a `discover_categories()` function that:
- Uses existing anti-blocking code
- Navigates megamenus
- Follows category links
- Used to work great

**Why it's blocked now:**
- Lowes tightened bot detection recently
- May work again in the future
- Could work from residential IP
- Could work with manual session warmup first

## Understanding URL Types

### `/pl/` URLs - Product Listings (What you want!)
```
https://www.lowes.com/pl/Bathroom-faucets-Bathroom/4294821341
```
- Shows grid of products
- These are your target URLs
- Non-redundant when properly chosen
- Each represents a unique category

### `/c/` URLs - Category Pages (Sometimes useful)
```
https://www.lowes.com/c/Plumbing
```
- May contain "Shop All" buttons → /pl/ URL
- May contain subcategories → more /c/ URLs
- Need to explore to find actual product listings

## Avoiding Redundancy

The goal is **non-redundant coverage** of all Lowes products. Key principles:

1. **Prefer specific over general**
   - "Bathroom Faucets" over "Bathroom"
   - "LED Bulbs" over "Light Bulbs"

2. **Avoid duplicate hierarchies**
   - If you have "Tools > Hand Tools > Hammers", don't also scrape "Tools" and "Hand Tools"
   - Go to the most specific category

3. **Shop All buttons are gold**
   - A "Shop All" button for a /c/ category = its comprehensive /pl/ URL
   - Prefer these over exploring deeper

4. **Check the breadcrumbs**
   - Products in "A > B > C" shouldn't also appear in just "A > B"
   - Lowes usually structures properly

## Recommended Workflow

### Phase 1: Quick Manual Capture (30 minutes)
```bash
python manual_url_capture.py
```
- Open every main department
- Expand menus
- Click "Shop All" when you see it
- Let script capture everything
- Result: ~500-1000 URLs

### Phase 2: Deduplication
```bash
# Combine with existing catalog
cat catalog/legacy_building_materials.lowes.yml | grep "url:" | awk '{print $2}' > existing_urls.txt
cat manual_captured_pl_TIMESTAMP.txt >> existing_urls.txt

# Remove duplicates
sort existing_urls.txt | uniq > all_unique_lowes_urls.txt
```

### Phase 3: Validation (Optional)
Create script to:
1. Check each URL still exists (HTTP 200)
2. Verify it's a product listing (has product grid)
3. Remove dead/redirected URLs

### Phase 4: Update Catalog
Convert to YAML format like your existing `legacy_building_materials.lowes.yml`

## Advanced: Automated with Manual Warmup

If you want automation to work:

1. **Warmup phase (manual):**
   - Browse Lowes normally for 5 minutes
   - Add items to cart
   - Search for products
   - Build "normal user" profile

2. **Then run automated discovery:**
   - Uses same browser profile
   - Has cookies/history from warmup
   - More likely to succeed

Implement this by:
- Starting browser with persistent context
- Do manual warmup
- Then run `discover_categories()` in same session

## Files Created for You

1. `manual_url_capture.py` - Main recommended tool
2. `extract_from_sitemap.py` - Sitemap extraction attempt
3. `crawl_lowes_v2.py` - Automated crawler (blocked by Lowes)
4. `discover_all_lowes_urls.py` - Alternative automated approach (also blocked)
5. `run_category_discovery.py` - Uses your existing code (blocked)

## Current State of Your Catalog

**File:** `catalog/legacy_building_materials.lowes.yml`
- 193 URLs currently
- Mix of /pl/ and /c/ URLs
- Needs expansion to full Lowes catalog

**Estimated full catalog size:** 2,000-3,000 unique product listing URLs

## Next Steps

**I recommend:**

1. Run `python manual_url_capture.py` NOW
2. Spend 20-30 minutes clicking through Lowes
3. You'll capture 500+ URLs easily
4. Combine with your existing 193
5. Deduplicate
6. Update your catalog YAML

**Then for ongoing maintenance:**
- Rerun quarterly to catch new categories
- Takes just 30 minutes every few months
- Or try automated discovery periodically (Lowes may relax detection)

## Why This Isn't Ideal But Is Necessary

I tried **everything** to automate this:
- ✗ Standard Playwright crawler
- ✗ With playwright-stealth
- ✗ With device emulation
- ✗ With your proven anti-blocking code
- ✗ Using your existing discover_categories()
- ✗ Headless and non-headless
- ✗ Different wait strategies
- ✗ Sitemap access

Lowes blocks them all. They likely use:
- TLS fingerprinting
- Canvas/WebGL fingerprinting
- Behavior analysis
- DataCenter IP detection
- Automation markers we can't hide

The **only reliable method** is real human interaction, which `manual_url_capture.py` facilitates efficiently.

## Future: When Automation Might Work Again

Watch for:
- Lowes policy changes
- Using residential proxy services
- Undetected ChromeDriver alternatives
- New stealth techniques
- Running from non-datacenter IPs

Your existing code is excellent and ready to use when/if Lowes relaxes restrictions.
