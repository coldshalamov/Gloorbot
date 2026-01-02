"""Quick script to check the contents of lowes_products.db"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "lowes_products.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
c = conn.cursor()

# Check total products
c.execute("SELECT COUNT(*) FROM products")
total = c.fetchone()[0]
print(f"📊 Total products in database: {total:,}")

if total > 0:
    # Check by store
    print("\n📍 Products by store:")
    c.execute("SELECT store_name, COUNT(*) as count FROM products GROUP BY store_name ORDER BY count DESC LIMIT 10")
    for store, count in c.fetchall():
        print(f"  {store}: {count:,} products")
    
    # Check recent products
    print("\n🕐 Most recent products:")
    c.execute("SELECT title, price, store_name, timestamp FROM products ORDER BY timestamp DESC LIMIT 5")
    for title, price, store, ts in c.fetchall():
        print(f"  [{ts}] {title[:50]} - ${price} @ {store}")
    
    # Check date range
    c.execute("SELECT MIN(timestamp), MAX(timestamp) FROM products")
    min_ts, max_ts = c.fetchone()
    print(f"\n📅 Data range: {min_ts} to {max_ts}")
else:
    print("\n⚠️ Database is empty - no products scraped yet!")

conn.close()
