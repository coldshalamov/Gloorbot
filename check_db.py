import sqlite3

db_path = "lowes_products.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check total products
c.execute("SELECT COUNT(*) FROM products")
total = c.fetchone()[0]
print(f"📊 Total products in database: {total}")

if total > 0:
    # Check last 5 products
    c.execute("SELECT title, price, price_was, category, store_name FROM products ORDER BY id DESC LIMIT 5")
    print("\n🔍 Last 5 products scraped:")
    for i, row in enumerate(c.fetchall(), 1):
        title, price, price_was, category, store = row
        was_text = f" (was ${price_was})" if price_was else ""
        print(f"  {i}. [{store}] {title[:60]}...")
        print(f"     💰 ${price}{was_text} - {category}")
    
    # Check for potential bad prices (< $1)
    c.execute("SELECT COUNT(*) FROM products WHERE price < 1.0")
    bad_prices = c.fetchone()[0]
    if bad_prices > 0:
        print(f"\n⚠️  Warning: {bad_prices} products with price < $1.00 (may be parsing errors)")
        c.execute("SELECT title, price FROM products WHERE price < 1.0 LIMIT 3")
        for title, price in c.fetchall():
            print(f"     - {title[:50]}... ${price}")
else:
    print("\n📭 Database is empty - no products scraped yet")

conn.close()
