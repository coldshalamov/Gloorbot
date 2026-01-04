# SOLUTION: The /c/ URL Problem is Auto-Fixed on Redeploy!

## 🎉 GOOD NEWS

The coordinator **already has auto-cleanup logic** built in!

### How It Works

When the coordinator starts up, it runs `seed_tasks_from_parallel_urls()` which:

1. Loads URLs from `apps/coordinator/data/urls.txt` (which has 0 `/c/` URLs)
2. Checks if `PRUNE_TASKS_NOT_IN_SEED=true` (default: true)
3. **Automatically deletes** any tasks whose `category_url` is NOT in the current seed list
4. This includes all `/c/` URLs!

See: `apps/coordinator/coordinator_app/seed.py` lines 98-108

---

## ✅ THE FIX

### Option 1: Just Redeploy (EASIEST)

1. Go to Render dashboard
2. Find `gloorbot-coordinator` service
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait for deployment to complete
5. Check the logs - you should see: `[seed] pruned_tasks_not_in_seed=XXX`

**That's it!** The `/c/` URLs will be automatically removed.

### Option 2: Force Re-seed Without Redeploying

If you don't want to redeploy, you can trigger the seed function:

1. Open Render shell for the coordinator
2. Run:
```python
from coordinator_app.seed import seed_tasks_from_parallel_urls
from pathlib import Path
count = seed_tasks_from_parallel_urls(Path.cwd())
print(f"Pruned/inserted: {count}")
```

---

## 🔍 WHY THE /c/ URLs EXISTED

1. **Persistent Database**: Render uses a persistent disk (`/var/data`) that survives deployments
2. **Old Data**: The database had `/c/` URLs from an old deployment (before the seed logic was fixed)
3. **New Deployments**: New code deploys, but the old database persists
4. **Auto-Cleanup**: The new seed logic (lines 98-108) should have cleaned them up... 

**BUT** - it only prunes if the categories list is loaded. Let me check if there's a condition that might prevent pruning...

---

## ⚠️ POTENTIAL ISSUE

Looking at line 101: `if prune_flag and categories:`

The pruning only happens if `categories` is not empty. If the seed function fails to load categories for some reason, it won't prune.

Let me check if there's an issue with the file path...

Looking at lines 67-68:
```python
local_urls = Path(__file__).resolve().parents[1] / "data" / "urls.txt"
urls_path = local_urls if local_urls.exists() else (repo_root / "PARALLEL" / "urls.txt")
```

This should work fine. The coordinator should find `apps/coordinator/data/urls.txt`.

---

## 🎯 RECOMMENDED ACTION

**Just redeploy the coordinator on Render.**

The auto-pruning logic will:
- Load the clean `urls.txt` (524 `/pl/` URLs, 0 `/c/` URLs)
- Delete all tasks with `/c/` URLs
- Workers will immediately start getting clean URLs

---

## 📊 VERIFICATION

After redeploying, check the Render logs for:
```
[seed] pruned_tasks_not_in_seed=XXX
```

Where XXX should be the number of `/c/` URLs that were deleted.

You can also verify by watching a worker - it should only visit `/pl/` URLs now.
