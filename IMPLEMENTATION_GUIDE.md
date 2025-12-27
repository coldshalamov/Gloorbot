# Implementation Guide: Adding New Categories to Lowe's Scraper

## Quick Reference

**File to Edit:** `lowes-apify-actor/src/main.py`
**Location:** Lines 485-528 (DEFAULT_CATEGORIES list)
**Current Count:** 23 categories
**Recommended Additions:** 5-14 categories (see below)

---

## Step-by-Step Implementation

### Step 1: Open the File

Navigate to and open:
```
lowes-apify-actor/src/main.py
```

### Step 2: Find the DEFAULT_CATEGORIES List

Look for line 485 which starts with:
```python
DEFAULT_CATEGORIES = [
```

### Step 3: Locate the Insertion Point

Scroll to the end of the list (around line 528) which currently looks like:
```python
    # Hardware
    {"name": "Fasteners", "url": "https://www.lowes.com/pl/Fasteners-Hardware/4294857976"},
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},
]
```

### Step 4: Add New Categories

**BEFORE THE CLOSING BRACKET `]`**, add a comma after the last entry and insert new categories.

**Example - Adding High Priority Categories:**

```python
    # Hardware
    {"name": "Fasteners", "url": "https://www.lowes.com/pl/Fasteners-Hardware/4294857976"},
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},

    # Lawn & Garden (NEW - HIGH PRIORITY)
    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},

    # Holiday (NEW - HIGH PRIORITY)
    {"name": "Holiday Decorations", "url": "https://www.lowes.com/c/Holiday-decorations"},

    # Home Decor (NEW - HIGH PRIORITY)
    {"name": "Home Decor & Furniture", "url": "https://www.lowes.com/c/Home-decor"},

    # Plumbing (NEW - HIGH PRIORITY)
    {"name": "Plumbing", "url": "https://www.lowes.com/c/Plumbing"},

    # HVAC (NEW - HIGH PRIORITY)
    {"name": "Heating & Cooling", "url": "https://www.lowes.com/c/Heating-cooling"},
]
```

**Important Notes:**
- Keep the comma after each entry (except the last one before `]`)
- Maintain consistent indentation (4 spaces)
- Keep comments for organization
- The list MUST end with `]` on its own line

---

## Ready-to-Copy Code Blocks

### Option 1: High Priority Only (Recommended First Step)

Copy everything between the markers and paste before the closing `]`:

```python
    # === HIGH PRIORITY ADDITIONS - ADD THESE FIRST ===

    # Lawn & Garden (Seasonal markdowns, outdoor equipment clearance)
    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},

    # Holiday Decorations (Major seasonal clearance events)
    {"name": "Holiday Decorations", "url": "https://www.lowes.com/c/Holiday-decorations"},

    # Home Decor & Furniture (Frequent markdowns, home staging products)
    {"name": "Home Decor & Furniture", "url": "https://www.lowes.com/c/Home-decor"},

    # Plumbing (High-ticket items, frequent promotions)
    {"name": "Plumbing", "url": "https://www.lowes.com/c/Plumbing"},

    # Heating & Cooling (Seasonal clearance, high-value items)
    {"name": "Heating & Cooling", "url": "https://www.lowes.com/c/Heating-cooling"},
```

**Result:** 28 total categories, 64% coverage (+20%)

---

### Option 2: High + Medium Priority (Comprehensive Coverage)

```python
    # === HIGH PRIORITY ADDITIONS ===

    # Lawn & Garden (Seasonal markdowns, outdoor equipment clearance)
    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},

    # Holiday Decorations (Major seasonal clearance events)
    {"name": "Holiday Decorations", "url": "https://www.lowes.com/c/Holiday-decorations"},

    # Home Decor & Furniture (Frequent markdowns, home staging products)
    {"name": "Home Decor & Furniture", "url": "https://www.lowes.com/c/Home-decor"},

    # Plumbing (High-ticket items, frequent promotions)
    {"name": "Plumbing", "url": "https://www.lowes.com/c/Plumbing"},

    # Heating & Cooling (Seasonal clearance, high-value items)
    {"name": "Heating & Cooling", "url": "https://www.lowes.com/c/Heating-cooling"},

    # === MEDIUM PRIORITY ADDITIONS ===

    # Doors & Windows (High-ticket items, occasional promotions)
    {"name": "Doors & Windows", "url": "https://www.lowes.com/c/Windows-doors"},

    # Storage & Organization (Seasonal sales - New Year organizing season)
    {"name": "Storage & Organization", "url": "https://www.lowes.com/c/Storage-organization"},

    # Cleaning Supplies (Regular promotions, bulk deals)
    {"name": "Cleaning Supplies", "url": "https://www.lowes.com/c/Cleaning-supplies"},

    # Smart Home & Security (Growing category, tech clearances)
    {"name": "Smart Home & Security", "url": "https://www.lowes.com/c/Smart-home-security-wi-fi"},

    # Moulding & Millwork (Construction materials, project-based sales)
    {"name": "Moulding & Millwork", "url": "https://www.lowes.com/c/Moulding-millwork"},
```

**Result:** 33 total categories, 84% coverage (+40%)

---

### Option 3: Complete Coverage (All Missing Departments)

```python
    # === HIGH PRIORITY ADDITIONS ===

    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},
    {"name": "Holiday Decorations", "url": "https://www.lowes.com/c/Holiday-decorations"},
    {"name": "Home Decor & Furniture", "url": "https://www.lowes.com/c/Home-decor"},
    {"name": "Plumbing", "url": "https://www.lowes.com/c/Plumbing"},
    {"name": "Heating & Cooling", "url": "https://www.lowes.com/c/Heating-cooling"},

    # === MEDIUM PRIORITY ADDITIONS ===

    {"name": "Doors & Windows", "url": "https://www.lowes.com/c/Windows-doors"},
    {"name": "Storage & Organization", "url": "https://www.lowes.com/c/Storage-organization"},
    {"name": "Cleaning Supplies", "url": "https://www.lowes.com/c/Cleaning-supplies"},
    {"name": "Smart Home & Security", "url": "https://www.lowes.com/c/Smart-home-security-wi-fi"},
    {"name": "Moulding & Millwork", "url": "https://www.lowes.com/c/Moulding-millwork"},

    # === LOWER PRIORITY ADDITIONS ===

    {"name": "Blinds & Window Treatments", "url": "https://www.lowes.com/c/Window-treatments-Home-decor"},
    {"name": "Automotive", "url": "https://www.lowes.com/c/Automotive"},
    {"name": "Sports & Fitness", "url": "https://www.lowes.com/c/Sports-fitness"},
    {"name": "Animal & Pet Care", "url": "https://www.lowes.com/c/Animal-pet-care"},
```

**Result:** 37 total categories, 100% coverage (+60%)

---

## After Adding Categories

### Step 5: Save the File

Save `main.py` with your changes.

### Step 6: Test the Configuration

Run the scraper locally to verify:
```bash
python lowes-apify-actor/src/main.py
```

### Step 7: Monitor Performance

Track the following metrics for new categories:
- Products found per category per run
- Number of markdowns detected
- Average markdown percentage
- Scraping time per category
- Error rate per category

### Step 8: Optimize Based on Results

After 1-2 weeks of monitoring:
- Keep categories with high markdown activity
- Remove or deprioritize categories with low activity
- Add more subcategories to high-performing departments
- Adjust scraping frequency based on markdown patterns

---

## Common Issues and Solutions

### Issue 1: Syntax Error After Adding Categories

**Error:** `SyntaxError: invalid syntax`

**Solution:** Check for:
- Missing comma after previous entry
- Extra comma after last entry before `]`
- Mismatched quotes in URL or name
- Incorrect indentation (use 4 spaces)

**Example - Incorrect:**
```python
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"}  # Missing comma!
    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},
]
```

**Example - Correct:**
```python
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},  # Has comma
    {"name": "Lawn & Garden", "url": "https://www.lowes.com/c/Lawn-garden"},
]
```

### Issue 2: Category Returns No Products

**Possible Causes:**
- URL changed on Lowe's website
- Category is seasonal and currently empty
- Bot protection blocking requests

**Solution:**
- Verify URL manually in a browser
- Check if category is seasonal
- Ensure scraper user-agent is set correctly
- Add retry logic with exponential backoff

### Issue 3: Duplicate Products Across Categories

**This is expected behavior** when:
- Parent and child categories overlap (e.g., "Appliances" + "Refrigerators")
- Product belongs to multiple categories

**Solution:**
- Deduplicate products by SKU/product ID in post-processing
- Keep the entry with the most recent timestamp
- OR keep all entries to track price changes across categories

---

## Performance Considerations

### Scraping Time Estimation

Based on current scraper performance:
- Average time per category: ~30-60 seconds
- Current 23 categories: ~20-30 minutes total
- With 28 categories (HIGH): ~25-35 minutes total
- With 33 categories (HIGH+MED): ~30-40 minutes total
- With 37 categories (ALL): ~35-45 minutes total

### Optimization Tips

1. **Parallel Processing:** Consider scraping multiple categories in parallel
2. **Smart Scheduling:** Run high-markdown categories more frequently
3. **Incremental Updates:** Only check clearance daily, others weekly
4. **Rate Limiting:** Add delays between requests to avoid bot detection

---

## Rollback Plan

If you need to revert changes:

### Option 1: Git Revert
```bash
cd lowes-apify-actor
git checkout src/main.py
```

### Option 2: Manual Revert

Remove the added categories by deleting the lines you added and restoring the original closing bracket:
```python
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},
]
```

---

## Success Metrics

After implementing the changes, track:

### Week 1-2 (Initial Testing)
- [ ] All new categories return products
- [ ] No scraping errors
- [ ] Performance within acceptable range
- [ ] Markdowns detected in new categories

### Month 1 (Performance Analysis)
- [ ] Markdown frequency per new category
- [ ] High-value items found
- [ ] ROI of additional scraping time
- [ ] Category ranking by markdown activity

### Ongoing (Optimization)
- [ ] Regular review of category performance
- [ ] Addition of high-performing subcategories
- [ ] Removal of low-performing categories
- [ ] Seasonal adjustments (Holiday in Nov-Dec, Lawn in Mar-Sep)

---

## Support and References

**Related Files:**
- `CATEGORY_AUDIT_REPORT.md` - Detailed analysis and findings
- `RECOMMENDED_CATEGORIES_TO_ADD.py` - Code snippets with explanations
- `category_analysis.json` - Machine-readable category data
- `AUDIT_SUMMARY.txt` - Quick reference summary

**Key Decisions:**
1. Start with HIGH priority categories (biggest impact, lowest risk)
2. Monitor for 1-2 weeks before adding more
3. Optimize based on actual performance data
4. Aim for 80%+ coverage of high-markdown departments

**Questions or Issues?**
- Review the detailed audit report for context
- Check Lowe's website to verify current category structure
- Test changes locally before deploying to Apify
- Monitor logs for errors after deployment

---

## Final Checklist

Before deploying your changes:

- [ ] Code is saved in `lowes-apify-actor/src/main.py`
- [ ] No syntax errors (commas, quotes, brackets)
- [ ] Indentation is consistent (4 spaces)
- [ ] Comments are clear and descriptive
- [ ] Tested locally without errors
- [ ] Git commit created with descriptive message
- [ ] Monitoring plan in place for new categories
- [ ] Rollback plan understood
- [ ] Expected impact documented

**Recommended First Deployment:**
- Add only HIGH priority categories (5 total)
- Monitor for 1 week
- Analyze results
- Proceed with MEDIUM priority if results are positive

---

**End of Implementation Guide**

For questions or detailed analysis, refer to `CATEGORY_AUDIT_REPORT.md`
