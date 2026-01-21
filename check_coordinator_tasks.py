"""
Quick script to show what tasks are currently in the coordinator database.
This helps verify that configuration changes are taking effect.
"""
import sqlite3
from pathlib import Path
from collections import Counter

# Find the coordinator database
db_paths = [
    Path("apps/coordinator/coordinator.sqlite"),
    Path("coordinator.sqlite"),
]

db_path = None
for path in db_paths:
    if path.exists():
        db_path = path
        break

if not db_path:
    print("❌ Could not find coordinator.sqlite database")
    exit(1)

print(f"📊 Reading tasks from: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get total task count
cursor.execute("SELECT COUNT(*) FROM tasks")
total = cursor.fetchone()[0]

# Get tasks by state
cursor.execute("SELECT state, COUNT(*) FROM tasks GROUP BY state ORDER BY state")
by_state = cursor.fetchall()

# Get tasks by store (top 10)
cursor.execute("""
    SELECT store_name, COUNT(*) as cnt 
    FROM tasks 
    GROUP BY store_name 
    ORDER BY cnt DESC 
    LIMIT 10
""")
top_stores = cursor.fetchall()

# Get sample category URLs
cursor.execute("SELECT DISTINCT category_url FROM tasks LIMIT 5")
sample_categories = [row[0] for row in cursor.fetchall()]

conn.close()

print(f"{'='*60}")
print(f"  COORDINATOR TASK DATABASE STATUS")
print(f"{'='*60}\n")

print(f"📦 Total Tasks: {total:,}\n")

if by_state:
    print("📍 Tasks by State:")
    for state, count in by_state:
        print(f"   {state}: {count:,} tasks")
    print()

if top_stores:
    print("🏪 Top 10 Stores (by task count):")
    for store, count in top_stores:
        print(f"   {store}: {count:,} tasks")
    print()

if sample_categories:
    print("🔗 Sample Category URLs:")
    for url in sample_categories:
        print(f"   {url}")
    print()

print(f"{'='*60}")

if total == 0:
    print("\n⚠️  No tasks found! Workers will have nothing to do.")
    print("   Go to the Admin Dashboard and save a configuration.")
elif 'FL' in [s for s, _ in by_state]:
    print("\n✅ Florida tasks detected! Workers should scrape FL stores.")
elif 'WA' in [s for s, _ in by_state] or 'OR' in [s for s, _ in by_state]:
    print("\n✅ WA/OR tasks detected! Workers should scrape Northwest stores.")
else:
    print(f"\n⚠️  Unexpected state configuration: {[s for s, _ in by_state]}")
