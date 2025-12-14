# Lowe's Scraper - Production Deployment Guide

## Version 2.1 - Parallel Architecture

**Deployed:** December 14, 2025
**Actor ID:** yVjX6SDnatnHFByJq
**Console:** https://console.apify.com/actors/yVjX6SDnatnHFByJq

---

## 🚀 What Changed in v2.1

### 1. **3x Parallel Execution**
- **Old:** Sequential (1 store at a time) = 16-34 hours
- **New:** 3 stores in parallel = **7-10 hours** ✅
- Architecture: Single browser, 3 concurrent contexts

### 2. **Enhanced Pickup Filter (CRITICAL)**
- **Multi-factor verification:**
  - ✅ Element state (`aria-checked`)
  - ✅ URL parameters (`?refinement=pickup`)
  - ✅ Product count validation (before/after)
- **Fail-fast:** Skips entire category if filter fails
- **Result:** Ensures ONLY local "Pickup Today" items are scraped

### 3. **Increased Memory**
- **Min:** 4GB (was 2GB)
- **Max:** 8GB (was 4GB)
- **Why:** 3 concurrent browser contexts

---

## 📊 Performance Estimates

### Full WA/OR Crawl (49 Stores × 24 Categories)

| Metric | Estimate |
|--------|----------|
| Total requests | ~11,760 |
| Duration | **7-10 hours** |
| Proxy data | ~6-8 GB |
| Proxy cost | ~$27-36 |
| Compute cost | ~$8-12 |
| **TOTAL COST** | **$35-48** |

### Breakdown by Batch

- 49 stores ÷ 3 parallel = **17 batches**
- Each batch: ~25-35 minutes
- Between batches: 2-4 sec delay

---

## 🔐 CRITICAL: Residential Proxy Required

### Why Free Tier Fails

```
ERR_INVALID_AUTH_CREDENTIALS
Proxy setup failed
```

**Cause:** Apify free tier only includes datacenter proxies
**Solution:** Upgrade to **Starter plan** ($49/month)

### What You Get

- ✅ 5 GB residential proxy traffic/month
- ✅ US residential IPs
- ✅ Session locking (required for Lowe's)
- ✅ Akamai bypass

### Upgrade Steps

1. Go to: https://console.apify.com/billing
2. Select **Starter** plan
3. Residential proxies auto-enable

---

## ⚙️ Configuration

### Input Schema

```json
{
  "stores": [],                     // Empty = all 49 WA/OR stores
  "categories": [],                 // Empty = all 24 categories
  "max_pages_per_category": 50      // 1,200 items per category max
}
```

### For Testing (Recommended First Run)

```json
{
  "stores": [
    {"store_id": "0004", "name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"}
  ],
  "categories": [
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}
  ],
  "max_pages_per_category": 5
}
```

**Expected:**
- Duration: ~2-3 minutes
- Cost: ~$0.50-1.00
- Products: 50-120 items

**Validates:**
- ✅ Residential proxies working
- ✅ No "Access Denied" errors
- ✅ Pickup filter applied correctly
- ✅ Data extraction accurate

### For Full Production Run

```json
{
  "stores": [],
  "categories": [],
  "max_pages_per_category": 50
}
```

---

## 🎯 How Pickup Filter Verification Works

### The Problem (Before v2.1)

Clicking the filter didn't guarantee it worked:
- Element clicked but page didn't update
- Race condition: clicked before page loaded
- No verification = scraped wrong data

### The Solution (v2.1)

**Triple verification after clicking:**

```
1. Check element state
   └─ aria-checked="true" or aria-pressed="true"

2. Check URL changed
   └─ ?refinement= or pickup/availability params

3. Check product count
   └─ Count decreased after filter
```

**If ALL 3 fail:** Skip category entirely (prevents bad data)

### Logs You'll See

**SUCCESS:**
```
[INFO] [Clearance] Clicking pickup filter: 'Get It Today'
[INFO] [Clearance] Pickup filter VERIFIED via url-params
[INFO] [Clearance] Products: 144 -> 72
```

**FAILURE (prevents bad data):**
```
[ERROR] [Paint] Pickup filter FAILED after 3 attempts - SKIPPING CATEGORY
```

---

## 📈 Monitoring Your Run

### Via Apify Console

1. Go to https://console.apify.com/actors/yVjX6SDnatnHFByJq/runs
2. Click latest run
3. Watch logs in real-time

### Key Log Messages

**Batch Progress:**
```
BATCH 1: Processing 3 stores in parallel
  STORE: Lowe's Rainier (0004)
  STORE: Lowe's Tukwila (0010)
  STORE: Lowe's N. Seattle (0252)
```

**Per-Category:**
```
[Lowe's Rainier] Clearance p1
  Pickup filter VERIFIED via element-state
  Found 24 products (total: 24)

[Lowe's Rainier] Clearance p2
  Found 21 products (total: 45)
```

**Completion:**
```
SCRAPING COMPLETE
Total products: 47,283
```

### Download Results

1. Go to **Storage** → **Dataset**
2. Click **Download**
3. Format: JSON or CSV

---

## 🔍 Output Schema

```json
{
  "store_id": "0004",
  "store_name": "Lowe's Rainier",
  "sku": "1000123456",
  "title": "DEWALT 20V MAX Cordless Drill/Driver Kit",
  "category": "Power Tools",
  "price": 99.00,
  "price_was": 149.00,
  "pct_off": 0.3356,
  "availability": "In Stock",
  "clearance": true,
  "product_url": "https://www.lowes.com/pd/DEWALT-...",
  "image_url": "https://mobileimages.lowes.com/...",
  "timestamp": "2025-12-14T08:15:00Z"
}
```

### Key Fields

- `clearance`: Auto-detected (25%+ discount or "Clearance" label)
- `pct_off`: Decimal (0.3356 = 33.56% off)
- `availability`: Always "In Stock" (pickup filter ensures this)
- `timestamp`: UTC ISO format

---

## 🛠️ Troubleshooting

### "Access Denied" Errors

**Symptom:**
```
[ERROR] BLOCKED by Akamai!
```

**Cause:** Not using residential proxies
**Fix:** Upgrade to Starter plan

### Empty Results / No Products

**Symptom:**
```
[Clearance] Found 0 products
```

**Causes:**
1. Pickup filter failed → Check logs for "VERIFIED"
2. Category doesn't exist for that store → Normal (skip)
3. Page crash → Rare, auto-recovers

### High Costs

**Symptom:** Cost > $50

**Causes:**
1. Too many pages → Reduce `max_pages_per_category` to 30
2. Images not blocked → Check resource blocking logs
3. Retries on blocks → Check for "BLOCKED" in logs

**Fix:**
```json
{
  "max_pages_per_category": 30    // Reduces cost by ~40%
}
```

---

## 📝 Architecture Details

### Parallelization

```python
# Process stores in batches of 3
for i in range(0, 49, 3):
    batch = stores[i:i+3]

    # Run 3 stores concurrently
    tasks = [scrape_store(s) for s in batch]
    results = await asyncio.gather(*tasks)
```

### Session Locking

```python
# Each store gets locked proxy session
proxy_url = await proxy_config.new_url(
    session_id=f"lowes_{store_id}"
)

# Same IP for entire store scrape
context = await browser.new_context(
    proxy={"server": proxy_url}
)
```

### Resource Blocking

**Blocks:**
- Images (largest bandwidth)
- Fonts, media, ads
- Analytics (GA, Facebook Pixel)
- 3rd party scripts

**NEVER blocks:**
- lowes.com domains
- Akamai scripts (`/_sec/`, `/akam/`)
- Product data endpoints

**Savings:** ~60-70% bandwidth

---

## 🎛️ Advanced Configuration

### Adjust Parallelization

Edit `src/main.py` line 682:

```python
PARALLEL_CONTEXTS = 3  # Change to 2 for slower/cheaper, 4 for faster/costlier
```

| Contexts | Duration | Cost |
|----------|----------|------|
| 2 | 10-15h | $30-40 |
| 3 | 7-10h | $35-48 |
| 4 | 5-8h | $45-60 |

### Memory Tuning

Edit `.actor/actor.json`:

```json
{
  "minMemoryMbytes": 4096,  // Recommended minimum
  "maxMemoryMbytes": 8192   // Can increase to 16384 for 4+ contexts
}
```

---

## 📞 Support

**Issues:** https://github.com/anthropics/claude-code/issues
**Apify Docs:** https://docs.apify.com
**Actor Console:** https://console.apify.com/actors/yVjX6SDnatnHFByJq

---

## ✅ Pre-Flight Checklist

Before running full crawl:

- [ ] Upgraded to Apify Starter plan ($49/month)
- [ ] Residential proxies enabled (US region)
- [ ] Ran test with 1 store, 1 category
- [ ] Verified pickup filter logs show "VERIFIED"
- [ ] Confirmed no "Access Denied" errors
- [ ] Checked sample data looks correct
- [ ] Ready for 7-10 hour run

**When ready:** Click **Start** on Actor console!
