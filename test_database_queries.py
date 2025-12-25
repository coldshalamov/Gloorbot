#!/usr/bin/env python3
"""
Test database queries to verify schema and structure.
This script creates a test database and runs sample queries.
"""

import sys
import sqlite3
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def test_database():
    """Test database creation and queries."""

    db_path = 'test_lowes.db'

    # Create connection
    conn = sqlite3.connect(db_path)
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            browser_id TEXT,
            store_id TEXT,
            category TEXT,
            status TEXT,
            products_found INTEGER,
            error TEXT
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON products(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_store ON products(store_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sku ON products(sku)")

    conn.commit()
    print("✓ Database schema created successfully")

    # Insert test data
    now = datetime.now(timezone.utc).isoformat()
    test_products = [
        (now, "0004", "Lowe's Rainier", "SKU001", "Drill Set 20V", "Power Tools", 99.99, 149.99, 33.3, "In Stock", 0, "https://lowes.com/pd/SKU001", None),
        (now, "0004", "Lowe's Rainier", "SKU002", "Paint Roller Pack", "Paint", 12.50, None, None, "In Stock", 1, "https://lowes.com/pd/SKU002", None),
        (now, "1108", "Lowe's Tigard", "SKU003", "2x4 Lumber", "Lumber", 3.99, None, None, "In Stock", 0, "https://lowes.com/pd/SKU003", None),
        (now, "1108", "Lowe's Tigard", "SKU004", "LED Light Bulb", "Lighting", 5.99, 7.99, 25.0, "In Stock", 0, "https://lowes.com/pd/SKU004", None),
    ]

    for product in test_products:
        try:
            c.execute("""
                INSERT OR REPLACE INTO products
                (timestamp, store_id, store_name, sku, title, category, price, price_was, pct_off, availability, clearance, product_url, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product)
        except sqlite3.IntegrityError:
            pass

    # Log test data
    c.execute("""
        INSERT INTO scrape_log (timestamp, browser_id, store_id, category, status, products_found)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, "B1", "0004", "Power Tools", "SUCCESS", 2))

    c.execute("""
        INSERT INTO scrape_log (timestamp, browser_id, store_id, category, status, products_found)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, "B2", "1108", "Lumber", "SUCCESS", 1))

    conn.commit()
    print(f"✓ Inserted {len(test_products)} test products")

    # Test Query 1: Count by store
    print("\n" + "="*70)
    print("QUERY 1: Products by Store")
    print("="*70)
    c.execute("""
        SELECT store_id, store_name, COUNT(*) as count
        FROM products
        GROUP BY store_id, store_name
        ORDER BY store_id
    """)
    results = c.fetchall()
    for row in results:
        print(f"  {row[0]} ({row[1]}): {row[2]} products")

    # Test Query 2: Find sale items (price_was is NOT NULL)
    print("\n" + "="*70)
    print("QUERY 2: Sale Items (price_was IS NOT NULL)")
    print("="*70)
    c.execute("""
        SELECT sku, title, price, price_was, pct_off
        FROM products
        WHERE price_was IS NOT NULL
        ORDER BY pct_off DESC
    """)
    results = c.fetchall()
    if results:
        for row in results:
            print(f"  SKU {row[0]}: {row[1]}")
            print(f"    Price: ${row[2]:.2f} (was ${row[3]:.2f}) - {row[4]:.0f}% off")
    else:
        print("  ⚠ No sale items found (price_was is always NULL)")

    # Test Query 3: Clearance items
    print("\n" + "="*70)
    print("QUERY 3: Clearance Items (clearance = 1)")
    print("="*70)
    c.execute("""
        SELECT sku, title, price, category
        FROM products
        WHERE clearance = 1
        ORDER BY price DESC
    """)
    results = c.fetchall()
    if results:
        for row in results:
            print(f"  {row[1]} (SKU {row[0]}): ${row[2]:.2f} - {row[3]}")
    else:
        print("  ⚠ No clearance items found (always hardcoded to 0)")

    # Test Query 4: Products by category
    print("\n" + "="*70)
    print("QUERY 4: Products by Category")
    print("="*70)
    c.execute("""
        SELECT category, COUNT(*) as count, AVG(price) as avg_price
        FROM products
        GROUP BY category
        ORDER BY category
    """)
    results = c.fetchall()
    for row in results:
        print(f"  {row[0]}: {row[1]} products (avg: ${row[2]:.2f})")

    # Test Query 5: Image URL coverage
    print("\n" + "="*70)
    print("QUERY 5: Image URL Coverage")
    print("="*70)
    c.execute("SELECT COUNT(*) FROM products WHERE image_url IS NOT NULL")
    with_images = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    total = c.fetchone()[0]
    coverage = (with_images / total * 100) if total > 0 else 0
    print(f"  {with_images}/{total} products have image_url ({coverage:.1f}%)")
    if coverage == 0:
        print("  ⚠ Image URLs NOT CAPTURED - hardcoded to NULL")

    # Test Query 6: Scrape log
    print("\n" + "="*70)
    print("QUERY 6: Scrape Log Summary")
    print("="*70)
    c.execute("""
        SELECT status, COUNT(*) as count, SUM(products_found) as total_products
        FROM scrape_log
        GROUP BY status
    """)
    results = c.fetchall()
    for row in results:
        print(f"  {row[0]}: {row[1]} attempts, {row[2] or 0} products")

    # Test Query 7: Can recreate Lowe's with current data?
    print("\n" + "="*70)
    print("RECREATION CAPABILITY CHECK")
    print("="*70)

    required_fields = {
        'sku': 'Product ID',
        'title': 'Product Name',
        'price': 'Current Price',
        'product_url': 'Link to Real Lowe\'s',
        'image_url': 'Product Image',
        'price_was': 'Sale Price',
        'category': 'Category'
    }

    c.execute("PRAGMA table_info(products)")
    columns = {row[1] for row in c.fetchall()}

    print("  Essential fields for Lowe's recreation:")
    essential = ['title', 'price', 'image_url', 'category']
    for field in essential:
        if field in columns:
            # Check if data is populated
            c.execute(f"SELECT COUNT(*) FROM products WHERE {field} IS NOT NULL")
            count = c.fetchone()[0]
            total = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            coverage = (count / total * 100) if total > 0 else 0
            status = "✓" if coverage == 100 else "✗"
            print(f"    {status} {field}: {coverage:.0f}% coverage")

    conn.close()

    print("\n" + "="*70)
    print("DATABASE TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_database()
