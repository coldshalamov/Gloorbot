"""
Check the coordinator database for /c/ URLs and other problematic URLs
"""
import sqlite3
from pathlib import Path

# Find the coordinator database
db_paths = [
    Path("apps/coordinator/coordinator.db"),
    Path("apps/coordinator/coordinator.sqlite"),
    Path("coordinator.db"),
    Path("coordinator.sqlite"),
]

db_path = None
for p in db_paths:
    if p.exists():
        db_path = p
        break

if not db_path:
    print("❌ Could not find coordinator database")
    print("Checked:")
    for p in db_paths:
        print(f"   - {p.absolute()}")
    exit(1)

print(f"📊 Using database: {db_path.absolute()}\n")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check total tasks
c.execute("SELECT COUNT(*) FROM tasks")
total = c.fetchone()[0]
print(f"Total tasks: {total}")

# Check for /c/ URLs
c.execute("SELECT COUNT(*) FROM tasks WHERE category_url LIKE '%/c/%'")
c_urls_count = c.fetchone()[0]
print(f"/c/ URLs (category pages, NO PRODUCTS): {c_urls_count}")

if c_urls_count > 0:
    print("\n🔴 Found /c/ URLs in database:")
    c.execute("SELECT DISTINCT category_url FROM tasks WHERE category_url LIKE '%/c/%' LIMIT 20")
    for (url,) in c.fetchall():
        print(f"   - {url}")
    
    # Ask if we should remove them
    print(f"\n⚠️  These {c_urls_count} tasks will loop forever (no products to scrape)")
    print("They should be removed from the database.")

# Check for /pl/ URLs
c.execute("SELECT COUNT(*) FROM tasks WHERE category_url LIKE '%/pl/%'")
pl_urls_count = c.fetchone()[0]
print(f"\n✅ /pl/ URLs (product listings, GOOD): {pl_urls_count}")

# Check for parent category patterns (URLs that might not have products)
# Parent categories often have just 2 segments: /pl/Category-Name/ID
c.execute("""
    SELECT category_url, COUNT(*) as task_count 
    FROM tasks 
    WHERE category_url LIKE '%/pl/%'
    GROUP BY category_url 
    ORDER BY task_count DESC 
    LIMIT 10
""")
print("\n📋 Top 10 most common category URLs:")
for url, count in c.fetchall():
    segments = url.split('/pl/')[1].split('/') if '/pl/' in url else []
    status = "🟢" if len(segments) >= 2 else "🟡"
    print(f"   {status} {url} ({count} tasks)")

# Check task states
c.execute("""
    SELECT state, COUNT(*) 
    FROM tasks 
    GROUP BY state
""")
print("\n📊 Task states:")
for state, count in c.fetchall():
    print(f"   {state}: {count}")

# Generate cleanup SQL
if c_urls_count > 0:
    print("\n\n🔧 TO FIX: Run this SQL to remove /c/ URLs:")
    print("="*70)
    print(f"DELETE FROM tasks WHERE category_url LIKE '%/c/%';")
    print("="*70)
    print(f"\nThis will remove {c_urls_count} tasks that can never complete.")

conn.close()
