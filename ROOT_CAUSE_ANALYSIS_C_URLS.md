# ROOT CAUSE ANALYSIS: /c/ URLs Mystery

## 🔍 INVESTIGATION SUMMARY

After thorough investigation, here's what we found:

### ✅ CONFIRMED: No /c/ URLs in Source Code
1. **Current files**: 0 `/c/` URLs in all URL lists
2. **Git history**: 0 `/c/` URLs in any historical commit
3. **Seed logic**: Has ALWAYS filtered to only `/pl/` URLs (since at least commit 47f28e3d)
4. **Worker code**: Doesn't discover or generate URLs - only gets them from coordinator API
5. **Coordinator code**: Only creates tasks from seed file - no dynamic URL generation

### 🔴 THE MYSTERY

The `/c/` URLs in the Render database **were never added by any code in this repo**.

### 🎯 POSSIBLE EXPLANATIONS

#### Theory 1: Manual Database Seeding (MOST LIKELY)
Someone may have manually added URLs to the database:
- Via SQL console
- Via a one-time script
- Via an API call (though no such endpoint exists)
- During initial testing/development

#### Theory 2: Old/Different Codebase
The Render deployment might have been seeded from a different codebase:
- A fork or branch with different seed logic
- An old version before this repo existed
- A completely different scraper project

#### Theory 3: LLM-Generated URL List
You mentioned "the LLM that compiled the list" - perhaps:
- An LLM was asked to generate Lowe's URLs
- It generated both `/pl/` and `/c/` URLs
- These were manually added to the database
- The `/c/` URLs were later removed from files but not from the database

#### Theory 4: Database Migration/Import
The database might have been:
- Imported from another system
- Migrated from a different format
- Seeded from a CSV/JSON file that had `/c/` URLs

---

## 🔬 HOW TO VERIFY

### Check Render Deployment Logs
Look for the initial deployment logs to see what was seeded:
```
[seed] tasks_inserted=XXXX
```

### Check Database Creation Date
If you can access the Render database:
```sql
SELECT MIN(created_at) FROM tasks WHERE category_url LIKE '%/c/%';
```

This will tell you WHEN the `/c/` URLs were added.

### Check Task IDs
```sql
SELECT id, category_url FROM tasks WHERE category_url LIKE '%/c/%' ORDER BY id LIMIT 10;
```

Low task IDs = added early (possibly during initial seed)
High task IDs = added recently (possibly manual)

---

## 💡 THE REAL QUESTION

**Not "where are they coming from" but "where DID they come from"**

The `/c/` URLs are **legacy data** from the past. They're not being actively generated - they're just sitting in the persistent database.

The current code:
- ✅ Doesn't add `/c/` URLs
- ✅ Has auto-pruning to remove them
- ✅ Only seeds `/pl/` URLs

But the database persists between deployments, so old data remains until explicitly removed.

---

## ✅ THE SOLUTION (UNCHANGED)

**Redeploy the coordinator** - the auto-pruning will remove all `/c/` URLs.

OR

**Manually delete them**:
```sql
DELETE FROM tasks WHERE category_url LIKE '%/c/%';
```

---

## 📝 RECOMMENDATION

After fixing, add logging to track if `/c/` URLs ever appear again:

```python
# In seed.py, after loading categories:
c_urls = [url for url in categories if '/c/' in url]
if c_urls:
    print(f"[seed] WARNING: Found {len(c_urls)} /c/ URLs in seed file!")
    for url in c_urls[:5]:
        print(f"[seed]   - {url}")
```

This will alert you if `/c/` URLs somehow get into the seed file in the future.
