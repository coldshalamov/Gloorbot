# Realistic Cost Analysis - Lowe's Scraper

## The Hard Truth About Costs

**Residential proxies are 90%+ of your cost, regardless of where you run the compute.**

---

## Cost Breakdown by Component

### Compute Costs (Negligible)

| Platform | Cost | Runtime | Total |
|----------|------|---------|-------|
| AWS EC2 Spot (c6i.2xlarge) | $0.12/hr | 1 hour | **$0.12** |
| GCP Cloud Run | $0.000024/GB-sec | 1 hour | **$0.69** |
| Azure Container Instances | $0.000012/sec | 1 hour | **$0.43** |
| Hetzner Dedicated | $42/month | Unlimited | **$0** marginal |
| DigitalOcean Droplet | $0.071/hr | 1 hour | **$0.07** |
| **Apify** | $0.25/GB-hr | 200 GB-hrs | **$50** |

**Compute savings: $0.07-0.69 vs $50 on Apify**

---

### Proxy Costs (The Real Cost)

| Provider | $/GB | Quality | 2GB Cost | Block Rate |
|----------|------|---------|----------|------------|
| **Proxy-Cheap** | $5 | ⭐⭐⭐ | **$10** | 5-10% |
| **IPRoyal** | $7 | ⭐⭐⭐⭐ | **$14** | 2-3% |
| **Oxylabs** | $10 | ⭐⭐⭐⭐⭐ | **$20** | <1% |
| **Smartproxy** | $12.5 | ⭐⭐⭐⭐ | **$25** | 1-2% |
| **Bright Data** | $15 | ⭐⭐⭐⭐⭐ | **$30** | <1% |
| **Apify (bundled)** | ~$20 | ⭐⭐⭐⭐ | **$40** | 1-2% |

**Proxy costs: $10-40 (unavoidable for Akamai)**

---

## Total Cost Scenarios

### Scenario 1: Budget (Acceptable Quality)
```
Compute: AWS EC2 Spot          = $0.12
Proxies: Proxy-Cheap           = $10.00
────────────────────────────────────────
TOTAL:                           $10.12/crawl

Risk: 5-10% block rate, may need retries
Best for: Testing, low-frequency scraping
```

### Scenario 2: Balanced (Recommended)
```
Compute: AWS EC2 Spot          = $0.12
Proxies: Smartproxy            = $25.00
────────────────────────────────────────
TOTAL:                           $25.12/crawl

Risk: 1-2% block rate, reliable
Best for: Production, regular scraping
```

### Scenario 3: Premium (Highest Quality)
```
Compute: AWS EC2 Spot          = $0.12
Proxies: Bright Data           = $30.00
────────────────────────────────────────
TOTAL:                           $30.12/crawl

Risk: <1% block rate, most reliable
Best for: Mission-critical scraping
```

### Scenario 4: Apify (Managed Service)
```
Compute: Apify (bundled)       = $50.00
Proxies: Apify (bundled)       = $20-30
────────────────────────────────────────
TOTAL:                           $70-80/crawl

Risk: 1-2% block rate, fully managed
Best for: No DevOps, quick deployment
```

---

## Annual Cost Comparison

### If running 1x per day (365 crawls/year):

| Setup | Cost/Crawl | Annual Cost | vs Apify |
|-------|-----------|-------------|----------|
| **AWS + Proxy-Cheap** | $10.12 | **$3,694** | Save $22,306 |
| **AWS + Smartproxy** | $25.12 | **$9,169** | Save $16,831 |
| **AWS + Bright Data** | $30.12 | **$10,994** | Save $15,006 |
| **Apify** | $75 | **$27,375** | Baseline |

### If running 1x per week (52 crawls/year):

| Setup | Cost/Crawl | Annual Cost | vs Apify |
|-------|-----------|-------------|----------|
| **AWS + Proxy-Cheap** | $10.12 | **$526** | Save $3,374 |
| **AWS + Smartproxy** | $25.12 | **$1,306** | Save $2,594 |
| **AWS + Bright Data** | $30.12 | **$1,566** | Save $2,334 |
| **Apify** | $75 | **$3,900** | Baseline |

---

## Why Apify Costs More

### Apify's Markup Breakdown:
1. **Compute**: $50 (vs $0.12 on AWS Spot)
   - Markup: **417x**
   - Reason: Managed infrastructure, auto-scaling, monitoring

2. **Proxies**: $20-30 (vs $10-30 direct)
   - Markup: 0-2x
   - Reason: Convenience, no separate account needed

3. **Platform Fee**: Included
   - Features: Request queue, dataset storage, scheduling, monitoring

**You're paying for convenience, not just resources.**

---

## Break-Even Analysis

### When is Apify worth it?

**If your time is worth > $50/hour:**

Setup time for AWS:
- Initial: 4-6 hours
- Per-run maintenance: 0.5 hours

```
First run:
  AWS setup: 6 hours × $50/hr = $300
  AWS cost: $25
  Total: $325

Apify:
  Setup: 0.5 hours × $50/hr = $25
  Apify cost: $75
  Total: $100

Winner: Apify (for first run)

After 10 runs:
  AWS: $300 + (10 × $25) = $550
  Apify: $25 + (10 × $75) = $775
  
Winner: AWS (saves $225)

After 50 runs:
  AWS: $300 + (50 × $25) = $1,550
  Apify: $25 + (50 × $75) = $3,775
  
Winner: AWS (saves $2,225)
```

**Break-even: ~5 runs**

---

## My Recommendation

### For Your Use Case:

**Start with AWS + Proxy-Cheap ($10/crawl)**

Reasons:
1. **87% cost savings** vs Apify
2. You've already done the hard work (optimized scraper)
3. Setup time: 2-3 hours (I can help)
4. If block rate is too high, upgrade to Smartproxy

### Migration Path:

```
Week 1: Test with Proxy-Cheap
  ↓
  Block rate acceptable (<10%)?
  ↓
YES → Stick with it, save $60/crawl
NO → Upgrade to Smartproxy, save $45/crawl
```

---

## The Bottom Line

| Component | Apify | AWS DIY | Savings |
|-----------|-------|---------|---------|
| **Compute** | $50 | $0.12 | $49.88 |
| **Proxies** | $25 | $10-30 | $0-15 |
| **Setup Time** | 1 hour | 3 hours | -2 hours |
| **Maintenance** | 0 min/run | 5 min/run | -5 min |
| **Total (1 run)** | $75 | $10-30 | $45-65 |
| **Total (100 runs)** | $7,500 | $1,012-3,012 | $4,488-6,488 |

**At scale, AWS saves you thousands of dollars.**

---

## Action Items

1. ✅ **Done**: Optimized scraper (browser pooling)
2. ⏭️ **Next**: Choose proxy provider (start with Proxy-Cheap)
3. ⏭️ **Then**: Set up AWS EC2 Spot instance
4. ⏭️ **Test**: Run 1-2 test crawls
5. ⏭️ **Evaluate**: Check block rate and data quality
6. ⏭️ **Optimize**: Upgrade proxies if needed

**Want me to help with step 3 (AWS setup)?**
