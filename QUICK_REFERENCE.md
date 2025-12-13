# Quick Reference - Lowe's Scraper Optimization

## TL;DR

**Problem**: Scraper costs $400-500/crawl (109K browser instances)  
**Solution**: Browser pooling (50 browsers, 4 pages each)  
**Result**: $10-30/crawl (87-96% savings)

---

## Cost Cheat Sheet

| Setup | Total | Savings | Quality |
|-------|-------|---------|---------|
| **AWS + Proxy-Cheap** | $10 | 87% | ⭐⭐⭐ |
| **AWS + Smartproxy** | $25 | 67% | ⭐⭐⭐⭐ |
| **AWS + Bright Data** | $30 | 60% | ⭐⭐⭐⭐⭐ |
| Apify (baseline) | $75 | 0% | ⭐⭐⭐⭐ |

---

## Files You Need

### To Run Locally/AWS:
```
src/main_optimized.py      # Optimized scraper
src/proxy_config.py         # Proxy provider configs
requirements.txt            # Dependencies
input/LowesMap.txt          # Store & category data
```

### To Deploy to Apify:
```
src/main_optimized.py      # Upload as main.py
.actor/actor.json          # Apify configuration
Dockerfile                 # Container config
```

---

## Environment Variables

```bash
# Choose ONE proxy provider:

# Option 1: Proxy-Cheap ($10)
export PROXY_PROVIDER=proxy-cheap
export PROXYCHEAP_USERNAME=your_username
export PROXYCHEAP_PASSWORD=your_password

# Option 2: Smartproxy ($25)
export PROXY_PROVIDER=smartproxy
export SMARTPROXY_USERNAME=your_username
export SMARTPROXY_PASSWORD=your_password

# Option 3: Bright Data ($30)
export PROXY_PROVIDER=bright-data
export BRIGHT_DATA_USERNAME=your_username
export BRIGHT_DATA_PASSWORD=your_password
```

---

## Quick Start Commands

### Test Locally (12 URLs):
```bash
cd apify_actor_seed
python test_optimized.py
```

### Run Full Crawl (109K URLs):
```bash
python src/main_optimized.py
```

### Deploy to AWS:
```bash
# See AWS_DEPLOYMENT_GUIDE.md for full instructions
./deploy_scraper.sh
```

---

## Key Metrics to Monitor

✅ **Browser count**: Should be ≤ 50  
✅ **Memory usage**: ~400GB total (not 800GB+)  
✅ **Proxy sessions**: 50 (one per store)  
✅ **Block rate**: <10% (budget) or <2% (premium)  
✅ **Products found**: ~50K-100K (depends on inventory)  

---

## Troubleshooting

### "Too many browsers launching"
→ Check that you're using `main_optimized.py`, not `main.py`

### "Akamai blocks increasing"
→ Reduce `CONCURRENT_PAGES_PER_BROWSER` from 4 to 2
→ Or upgrade to better proxy provider

### "Out of memory"
→ Ensure browsers are closing properly
→ Check `browser_pool.close_all()` in finally block

### "Products missing"
→ Same as original - check pickup filter selectors
→ May need to update selectors if Lowe's changed their HTML

---

## Proxy Provider Sign-Up Links

- **Proxy-Cheap**: https://app.proxy-cheap.com/
- **Smartproxy**: https://smartproxy.com/
- **Bright Data**: https://brightdata.com/
- **IPRoyal**: https://iproyal.com/
- **Oxylabs**: https://oxylabs.io/

---

## Architecture Diagram

```
OLD (EXPENSIVE):
  109K URLs → 109K Browsers → $400-500

NEW (OPTIMIZED):
  50 Stores → 50 Browsers → 4 Pages Each → 200 Workers → $10-30
```

---

## Why Local Setup Failed

Your Verizon carrier IP setup failed because:

❌ Playwright TLS fingerprint (Akamai detects)  
❌ 30 parallel requests from ONE IP (obvious bot)  
❌ No session continuity (each browser = new session)  
❌ Behavioral patterns (inhuman speed)  

Residential proxies fix this by:

✅ Distributing requests across many IPs  
✅ Session locking per store (looks like one user)  
✅ Clean TLS fingerprints  
✅ Proper delays and navigation  

---

## Decision Tree

```
Do you need it working TODAY?
  YES → Use Apify ($75/crawl)
  NO → Continue...

Will you run 10+ times?
  YES → Use AWS (saves $450-650)
  NO → Use Apify (saves setup time)

What's your budget per crawl?
  $10 → Proxy-Cheap (5-10% blocks)
  $25 → Smartproxy (1-2% blocks)
  $30 → Bright Data (<1% blocks)
```

---

## Support

📖 **Full Documentation**:
- `COST_OPTIMIZATION_SOLUTION.md` - Technical details
- `REALISTIC_COST_ANALYSIS.md` - Cost breakdown
- `AWS_DEPLOYMENT_GUIDE.md` - AWS setup
- `README_OPTIMIZATION.md` - Complete overview

🚀 **Ready to deploy? Let me know which option you choose!**
