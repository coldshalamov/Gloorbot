# Intelligent Strategy for Finding Minimal Category Set

## The Problem

You have 815 unique categories across two files. Scraping all 815 would:
- Cost 58% more (vs your current 515)
- But might only give 10-20% more unique products (if there's heavy overlap)
- Wasteful duplication

## The Solution: Set Cover Optimization

Find the **minimum subset of categories** that covers **99%+ of all unique products**.

This is a classic "Set Cover" problem in computer science.

### Strategy

1. **Sample 80 categories** strategically (first 2 pages each)
   - This gives us ~500-1000 product samples
   - Enough to identify patterns

2. **Identify suspicious categories** that are definitely duplicates:
   - `SHOP-*` or `Shop-*` (promotional/deal pages)
   - `New-and-Trending-*` (curated subset)
   - Brand-specific pages: `Google--*`, `Ecobee--*`, `Klein-tools`
   - These are ~100% redundant with regular categories

3. **Track product overlap**:
   - Which products appear in multiple categories?
   - If 40%+ products appear in multiple categories → high overlap, need fewer categories
   - If <10% overlap → categories are mostly distinct, need more categories

4. **Use Greedy Set Cover algorithm**:
   - Start with empty set
   - Repeatedly pick the category that covers the most uncovered products
   - Stop when 99%+ coverage is reached
   - Result: Minimal set that covers everything

### Example

**Scenario A (High Overlap)**:
- Sample 80 categories = 1000 products scraped
- But only 650 unique products (65% duplication)
- Minimal set = ~35-40 categories to reach 99% coverage
- **Savings**: Use 40 instead of 815 → 95% cost reduction ✅

**Scenario B (Low Overlap)**:
- Sample 80 categories = 1000 products scraped
- All 1000 are unique (no duplication)
- Minimal set = ~75-80 categories
- **Extrapolate**: Need ~760 of 815 total categories
- **Cost**: Almost as much as union (not great, but at least we know)

## What We'll Find Out

After running the analysis, we'll know:

1. **Actual duplication rate**: What % of products appear in multiple categories?
2. **Minimal set size**: How many categories do we really need? (e.g., 40? 200? 600?)
3. **Suspicious categories to exclude**: Which ones are definitely promotional garbage?
4. **The breakdown**:
   - How many from Current (515)?
   - How many from Pruned (716)?
   - Can we skip some entirely?

## Why This Is Better Than Guessing

- **Data-driven**: Not based on assumptions
- **Quantified**: Will tell you exact % savings
- **Actionable**: Can create optimized category list immediately
- **Scalable**: Works for any product site

## Timeline

The script is running now:
- Samples 80 categories (10-15 mins total with network delays)
- Analyzes overlap patterns (< 1 min)
- Outputs minimal set recommendation

Once done, we'll know **exactly** which categories to scrape for 100% coverage at minimum cost.

## What Success Looks Like

**Best case**:
- Minimal set: ~40-50 categories (85% reduction from 815)
- Coverage: 99%+ of all products
- **Action**: Create optimized list, deploy to Apify

**Good case**:
- Minimal set: ~200-300 categories (60-75% reduction)
- Coverage: 99%+ of all products
- **Action**: Create optimized list, still major cost savings

**Bad case**:
- Minimal set: ~650+ categories (minimal reduction)
- Coverage: 99%+ of all products
- **Action**: Categories are mostly distinct, union (815) is necessary

Even in the bad case, at least we **know** and can make informed decision instead of guessing.
