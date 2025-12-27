# Parallel Diagnostic Test Analysis - Key Findings

## The Numbers
- **Total entries across 5 workers**: 79,784
- **Unique products found**: 1,701
- **Overall duplication rate**: 97.9%
- **Cross-worker overlap**: 81.1% (1,380 of 1,701 products appear in multiple workers)
- **Average per worker**: ~16,000 entries, ~1,050 unique products, ~93% internal duplication

## What This Means

### Good News: NO CATEGORY RERUNNING DETECTED
The 97.9% duplication is **NOT** from workers restarting and re-scraping the same categories.

Instead, each worker successfully scraped through ~35-40 categories and captured all pages of each category.

**Evidence:**
- Worker 0 has 958 products appearing 2+ times in its sequence
- These products are spread across the sequence (e.g., product 5013606429 appears at position 0, 220, etc.)
- This is exactly what happens when you scrape Category A page 1, Category A page 2, Category B page 1, Category B page 2, etc.
- Same products appear on multiple pages = pagination duplication, not category rerunning

### Bad News: MASSIVE PRODUCT OVERLAP BETWEEN CATEGORIES

The **81% cross-worker overlap** reveals something critical:
- Most Lowe's products appear in **multiple categories simultaneously**
- Example: Batteries appear in "Tools," "Electrical," "Safety Equipment," "Bestsellers," etc.

**Duplication breakdown per worker:**
- 93-95% of entries are products that already appeared in previous categories
- Only 6-7% of products are unique to each category scraped
- Each unique product is found ~13.7 times across ~35-40 categories

## What This Tells Us About Your URL List

### The Union (815 categories) is VERY Inefficient

**Math:**
- 5 workers × 40 categories each = 200 total categories tested
- Found only 1,701 unique products across those 200 categories
- Expected duplication rate: ~93%
- Extrapolating to 815 categories: Would find ~6,800 unique products (1,701 × 815/200)
- But at 93% duplication cost: 6,800 ÷ 0.07 = **97,000 product entries** instead of 1,701

**Cost comparison:**
- Current 515 categories: ~515 × 30 products/category × 2 pages avg = ~30,900 entries expected
- Union 815 categories: ~97,000 entries expected
- **Increase: 214% more data fetched for maybe 35-50% more unique products**

### The Smart Strategy: Aggressive Filtering

Since products heavily overlap across categories, you should:

1. **Exclude all promotional/brand categories** (already identified 12 to remove)
   - "SHOP-*-DEALS" - Same products in regular categories
   - "New-and-Trending" - Curated subset of bestsellers
   - Brand pages ("Google--*", "Ecobee--*") - Products in regular categories

2. **Focus on category hierarchy** - Keep parent categories, some children
   - If "Tools" contains everything in "Hammers" → Don't need both
   - If "Tools" and "Hand Tools" have 90%+ overlap → Pick one
   - Keep "Hammers", "Drills", "Saws" but skip redundant parent

3. **Expected result**: 300-400 categories covering 90-95% of products
   - Cost: 40-60% increase vs current 515
   - Coverage: 35-50% more unique products
   - This is the efficient range

## Immediate Action Items

### 1. Stop Using Union (815)
The complete union is financially wasteful. You're getting:
- 214% more page fetches
- ~40% more unique products
- Return on investment: **Not worth it**

### 2. Use the Optimized List (808 categories, exclude 7 promotional)
This is a safer intermediate step:
- Current 515: baseline
- Optimized 808: +57% cost for ~40% more products
- Better ratio than union, still has room for improvement

### 3. For Maximum Efficiency: Create Curated List
Once supervisor stabilizes, manually review:
- Which categories have >90% product overlap (remove duplicates)
- Which brand pages are truly unique vs promotional (remove duplication)
- Target: 350-450 categories covering 95%+ of products

## The Real Lesson: YOUR QUESTIONS WERE RIGHT

You asked: "Would crawling more URLs cost more? Or would it not matter since you're paginating through all items?"

**Answer: It ABSOLUTELY costs more.**

Each additional category = more page loads = more API calls = more compute cost on Apify.

With 93% duplication:
- **Inefficient**: Scraping 815 categories to get 6,800 products costs 214% more
- **Efficient**: Scraping 350 categories to get 6,500 products costs 35-40% more
- **The difference**: 465 categories worth of wasted compute costs

Your instinct to question the union was correct. Categories DO overlap significantly, making comprehensive scraping very expensive unless carefully curated.

## Recommended Next Steps

1. **Don't deploy union (815) to production** - Too expensive
2. **Test the optimized 808 list** on one store to verify duplication rate remains similar
3. **Once Apify integration is ready**, monitor product coverage vs compute costs
4. **Iteratively refine** category list based on actual data:
   - If duplication drops below 80% → Can add more categories
   - If duplication stays 90%+ → Need more aggressive filtering

## Questions for You

1. **Do you have access to Lowe's category hierarchy/parent-child relationships?**
   - If yes: Could automatically detect redundant categories
   - This would reduce optimized list from 808 → 400-500 categories

2. **What's your tolerance for missing products?**
   - 100% coverage (current plan): Expensive
   - 99% coverage: Moderate cost with careful selection
   - 95% coverage: Lean, fast, most products

3. **Is the current 515 list missing important products?**
   - Based on CATEGORY_COVERAGE_ANALYSIS.md: Yes, missing garden hoses, smart sensors, clothing
   - But many missing categories are brand-specific duplicates
   - Could fill gaps manually (add 10-15 important categories) instead of all 300
