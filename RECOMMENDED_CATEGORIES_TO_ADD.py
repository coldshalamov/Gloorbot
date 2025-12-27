# RECOMMENDED CATEGORIES TO ADD TO lowes-apify-actor/src/main.py
# Add these to the DEFAULT_CATEGORIES list

# ============================================================================
# HIGH PRIORITY ADDITIONS (Add these first)
# ============================================================================
# These departments have high markdown potential and seasonal clearance events

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


# ============================================================================
# MEDIUM PRIORITY ADDITIONS (Add after monitoring high-priority performance)
# ============================================================================

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


# ============================================================================
# LOWER PRIORITY ADDITIONS (Optional for 100% coverage)
# ============================================================================

# Blinds & Window Treatments (Niche category but occasional deals)
{"name": "Blinds & Window Treatments", "url": "https://www.lowes.com/c/Window-treatments-Home-decor"},

# Automotive (Small category at Lowe's)
{"name": "Automotive", "url": "https://www.lowes.com/c/Automotive"},

# Sports & Fitness (Limited selection at Lowe's)
{"name": "Sports & Fitness", "url": "https://www.lowes.com/c/Sports-fitness"},

# Animal & Pet Care (Small category, mostly outdoor pet products)
{"name": "Animal & Pet Care", "url": "https://www.lowes.com/c/Animal-pet-care"},


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
# 1. Open lowes-apify-actor/src/main.py
# 2. Find the DEFAULT_CATEGORIES list (around line 485)
# 3. Add the desired categories from above to the list
# 4. Save and test the scraper
# 5. Monitor performance and markdown frequency for each new category
# 6. Remove or deprioritize categories with low activity

# EXPECTED IMPACT:
# - Adding HIGH priority (5 categories): 44% → 64% coverage
# - Adding MEDIUM priority (5 more): 64% → 84% coverage
# - Adding ALL recommendations (14 total): 44% → 100% coverage

# CURRENT COVERAGE: 23 categories, 11/25 departments (44%)
# WITH HIGH PRIORITY: 28 categories, 16/25 departments (64%)
# WITH ALL ADDITIONS: 37 categories, 25/25 departments (100%)
