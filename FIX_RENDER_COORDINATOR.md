# HOW TO FIX THE /c/ URL PROBLEM

## THE ISSUE

The worker installer connects to: `https://gloorbot-coordinator.onrender.com`

This remote coordinator has **legacy `/c/` URLs** in its database that cause infinite loops.

---

## THE FIX

You need to clean the Render coordinator's database.

### Option 1: Via Render Dashboard (Recommended)

1. Go to https://dashboard.render.com
2. Find your `gloorbot-coordinator` service
3. Click "Shell" to open a terminal
4. Run these commands:

```bash
# Connect to the database
python

# In Python shell:
import sqlite3
conn = sqlite3.connect('coordinator.sqlite')  # or whatever the DB path is
c = conn.cursor()

# Check how many /c/ URLs exist
c.execute("SELECT COUNT(*) FROM tasks WHERE category_url LIKE '%/c/%'")
print(f"Found {c.fetchone()[0]} /c/ URLs")

# Delete them
c.execute("DELETE FROM tasks WHERE category_url LIKE '%/c/%'")
conn.commit()
print(f"Deleted {c.rowcount} tasks")

# Verify
c.execute("SELECT COUNT(*) FROM tasks WHERE category_url LIKE '%/c/%'")
print(f"Remaining /c/ URLs: {c.fetchone()[0]}")

conn.close()
exit()
```

5. Restart the coordinator service

### Option 2: Via API (If you have admin access)

If the coordinator has an admin API endpoint, you could call it.

### Option 3: Redeploy with Clean Database

1. Delete the persistent disk (if any) attached to the coordinator
2. Redeploy the coordinator
3. It will seed from the clean `apps/coordinator/data/urls.txt` (which has 0 `/c/` URLs)

---

## VERIFICATION

After cleaning, verify the workers are getting good URLs:

1. Watch a running worker
2. Check the URLs it's visiting
3. Should only see `/pl/` URLs now

You can also check the coordinator's status endpoint:
```bash
curl https://gloorbot-coordinator.onrender.com/api/v1/status
```

---

## WHY THIS HAPPENED

1. The coordinator database had old `/c/` URLs from before the seed logic was fixed
2. The seed logic (line 56 of `seed.py`) now filters to only `/pl/` URLs
3. But existing database records weren't cleaned up
4. Workers kept getting these bad URLs from the database

---

## PREVENTION

The fix is already in place:
- `seed.py` line 56 only loads `/pl/` URLs
- `seed.py` lines 100-108 prune tasks not in the seed list
- Future deployments won't have this problem

But you need to clean the **existing** database once.
