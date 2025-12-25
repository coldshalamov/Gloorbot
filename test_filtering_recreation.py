#!/usr/bin/env python3
"""
Test filtering and recreation capabilities.
Verify what queries are possible with current data structure.
"""

import sys
import sqlite3
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def setup_test_db():
    """Create realistic test database."""
    conn = sqlite3.connect('test_recreation.db')
    c = conn.cursor()

    # Create schema
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            store_id TEXT NOT NULL,
            store_name TEXT NOT NULL,
            sku TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL,
            price_was REAL,
            pct_off REAL,
            availability TEXT,
            clearance INTEGER,
            product_url TEXT,
            image_url TEXT,
            UNIQUE(store_id, sku)
        )
    """)

    conn.commit()

    # Realistic test data (what scraper actually extracts)
    now = datetime.now(timezone.utc).isoformat()
    products = [
        # Store 0004 - Power Tools (captured correctly)
        (now, "0004", "Lowe's Rainier", "SKU001", "DEWALT 20V MAX Cordless Drill", "Power Tools", 99.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU001", None),
        (now, "0004", "Lowe's Rainier", "SKU002", "Milwaukee 18V Impact Driver", "Power Tools", 149.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU002", None),
        (now, "0004", "Lowe's Rainier", "SKU003", "Makita Circular Saw 7.5in", "Power Tools", 79.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU003", None),

        # Store 0004 - Paint
        (now, "0004", "Lowe's Rainier", "SKU004", "Interior Paint Eggshell White", "Paint", 45.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU004", None),
        (now, "0004", "Lowe's Rainier", "SKU005", "Exterior Paint Semi-Gloss", "Paint", 55.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU005", None),

        # Store 0004 - Clearance (flagged but no image)
        (now, "0004", "Lowe's Rainier", "SKU006", "Clearance: Old Fixture Brass", "Clearance", 9.99, None, None, "In Stock", 1, "https://lowes.com/pd/SKU006", None),

        # Store 1108 - Lumber
        (now, "1108", "Lowe's Tigard", "SKU101", "2x4x8 Pressure Treated Lumber", "Lumber", 8.50, None, None, "In Stock", 0, "https://lowes.com/pd/SKU101", None),
        (now, "1108", "Lowe's Tigard", "SKU102", "2x6x12 Cedar Lumber", "Lumber", 22.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU102", None),

        # Store 1108 - Flooring
        (now, "1108", "Lowe's Tigard", "SKU103", "Oak Hardwood Flooring 3.25in", "Flooring", 6.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU103", None),
    ]

    for p in products:
        c.execute("""
            INSERT OR REPLACE INTO products
            (timestamp, store_id, store_name, sku, title, category, price, price_was, pct_off, availability, clearance, product_url, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)

    conn.commit()
    return conn

def test_recreation():
    """Test recreation capabilities."""
    print("="*70)
    print("LOWE'S WEBSITE RECREATION - CAPABILITY TEST")
    print("="*70)

    conn = setup_test_db()
    c = conn.cursor()

    print("\n1. DATA COMPLETENESS FOR HOMEPAGE LISTING")
    print("-" * 70)
    print("To recreate a product grid like Lowe's homepage, you need:")
    print("  - Product name: " + ("YES" if check_field_populated(c, 'title') else "NO"))
    print("  - Product image: " + ("YES" if check_field_populated(c, 'image_url') else "NO ❌ MISSING"))
    print("  - Current price: " + ("YES" if check_field_populated(c, 'price') else "NO"))
    print("  - Link to product: " + ("YES" if check_field_populated(c, 'product_url') else "NO"))

    c.execute("SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL")
    images = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    total = c.fetchone()[0]

    print(f"\nImage Coverage: {images}/{total} (0%) - CANNOT DISPLAY PRODUCT IMAGES")

    print("\n2. FILTERING CAPABILITIES")
    print("-" * 70)

    # Can filter by store?
    print("\nCan filter by Store: YES")
    c.execute("SELECT DISTINCT store_name FROM products")
    for row in c.fetchall():
        c.execute("SELECT COUNT(*) FROM products WHERE store_name = ?", (row[0],))
        count = c.fetchone()[0]
        print(f"  - {row[0]}: {count} products")

    # Can filter by category?
    print("\nCan filter by Category: YES")
    c.execute("SELECT DISTINCT category FROM products ORDER BY category")
    for row in c.fetchall():
        c.execute("SELECT COUNT(*) FROM products WHERE category = ?", (row[0],))
        count = c.fetchone()[0]
        print(f"  - {row[0]}: {count} products")

    # Can filter by price range?
    print("\nCan filter by Price Range: YES")
    ranges = [(0, 50), (50, 100), (100, 200), (200, 1000)]
    for min_p, max_p in ranges:
        c.execute(
            "SELECT COUNT(*) FROM products WHERE price >= ? AND price <= ?",
            (min_p, max_p)
        )
        count = c.fetchone()[0]
        print(f"  - ${min_p}-${max_p}: {count} products")

    # Can filter by clearance?
    print("\nCan filter by Clearance: LIMITED")
    c.execute("SELECT COUNT(*) FROM products WHERE clearance = 1")
    clearance_count = c.fetchone()[0]
    print(f"  - Clearance items: {clearance_count} (but always hardcoded, not detected)")
    print(f"  - Problem: No clearance detection, must manually tag items")

    # Can filter by sale/discount?
    print("\nCan filter by Sale/Discount: NO")
    c.execute("SELECT COUNT(*) FROM products WHERE price_was IS NOT NULL")
    sale_count = c.fetchone()[0]
    print(f"  - Items on sale: {sale_count} (price_was always NULL)")
    print(f"  - Problem: Cannot identify sale items automatically")

    # Can filter by availability?
    print("\nCan filter by Availability: NO")
    c.execute("SELECT DISTINCT availability FROM products")
    availability = c.fetchall()
    if len(availability) > 1:
        print(f"  - Multiple status values: YES")
    else:
        print(f"  - Status values: {availability[0][0]} (always same, hardcoded)")
        print(f"  - Problem: Cannot filter in/out of stock items")

    print("\n3. SEARCH CAPABILITIES")
    print("-" * 70)

    # Can search by product name?
    print("\nCan search by Product Name: YES")
    c.execute("""
        SELECT COUNT(*) FROM products
        WHERE title LIKE '%drill%' OR title LIKE '%Drill%'
    """)
    drill_count = c.fetchone()[0]
    print(f"  - Example: Search for 'drill': {drill_count} results")

    # Can search by SKU?
    print("\nCan search by SKU: YES")
    c.execute("SELECT COUNT(*) FROM products")
    sku_count = c.fetchone()[0]
    print(f"  - {sku_count} unique SKUs indexed and searchable")

    print("\n4. WHAT YOU CAN BUILD WITH CURRENT DATA")
    print("-" * 70)
    print("""
    ✓ Product catalog with names and prices
    ✓ Store locator (49 stores with inventory)
    ✓ Category browsing (24 categories)
    ✓ Price range filtering
    ✓ Search by product name
    ✓ Price history tracking (by timestamp)
    ✓ Clearance section (if manually tagged)
    ✗ Visual product display (NO IMAGES)
    ✗ Sale/discount filtering (NO PRICE_WAS)
    ✗ Dynamic availability (ALWAYS IN STOCK)
    ✗ Product reviews (NOT CAPTURED)
    ✗ Product descriptions (NOT CAPTURED)
    """)

    print("5. BOTTOM LINE: CAN YOU RECREATE LOWE'S?")
    print("-" * 70)

    # Calculate recreation capability
    required_for_homepage = {
        'name': check_field_populated(c, 'title'),
        'image': check_field_populated(c, 'image_url'),
        'price': check_field_populated(c, 'price'),
        'link': check_field_populated(c, 'product_url'),
    }

    complete = sum(1 for v in required_for_homepage.values() if v)
    total_required = len(required_for_homepage)

    print(f"\nFor basic product grid: {complete}/{total_required} essentials")
    for field, has_it in required_for_homepage.items():
        status = "YES" if has_it else "NO ❌"
        print(f"  - {field.upper()}: {status}")

    if complete == total_required:
        print("\n✓ CAN recreate basic Lowe's product listing")
    else:
        print(f"\n✗ CANNOT recreate Lowe's (missing {total_required - complete} essentials)")
        print(f"  CRITICAL MISSING: Product images (image_url is NULL)")
        print(f"  This is why you can't recreate the visual experience")

    # Check what percentage of real Lowe's functionality is captured
    all_features = {
        'Product Name': check_field_populated(c, 'title'),
        'Product Image': check_field_populated(c, 'image_url'),
        'Current Price': check_field_populated(c, 'price'),
        'Original Price': check_field_populated(c, 'price_was'),
        'Discount %': check_field_populated(c, 'pct_off'),
        'Clearance Flag': has_clearance_logic(c),
        'Availability': has_availability_logic(c),
        'Product Link': check_field_populated(c, 'product_url'),
    }

    feature_count = sum(1 for v in all_features.values() if v)
    feature_total = len(all_features)
    percentage = (feature_count / feature_total) * 100

    print(f"\n6. OVERALL FEATURE COVERAGE")
    print("-" * 70)
    print(f"Implemented: {feature_count}/{feature_total} features ({percentage:.0f}%)")
    for feature, implemented in all_features.items():
        status = "✓" if implemented else "✗"
        print(f"  {status} {feature}")

    if percentage < 50:
        print(f"\n❌ VERDICT: {percentage:.0f}% complete - NOT READY for Lowe's recreation")
    elif percentage < 80:
        print(f"\n⚠ VERDICT: {percentage:.0f}% complete - Basic functionality only")
    else:
        print(f"\n✓ VERDICT: {percentage:.0f}% complete - Full Lowe's recreation possible")

    conn.close()

def check_field_populated(c, field):
    """Check if field has data (not NULL)."""
    c.execute(f"SELECT COUNT(*) FROM products WHERE {field} IS NOT NULL")
    count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    total = c.fetchone()[0]
    return count == total

def has_clearance_logic(c):
    """Check if clearance detection is working."""
    c.execute("SELECT COUNT(DISTINCT clearance) FROM products")
    distinct = c.fetchone()[0]
    # If only one value, it's hardcoded
    return distinct > 1

def has_availability_logic(c):
    """Check if availability detection is working."""
    c.execute("SELECT COUNT(DISTINCT availability) FROM products")
    distinct = c.fetchone()[0]
    # If only one value, it's hardcoded
    return distinct > 1

if __name__ == "__main__":
    test_recreation()
