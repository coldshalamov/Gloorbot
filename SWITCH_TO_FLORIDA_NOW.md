# URGENT: How to Switch Workers to Florida

## What's Happening
Your workers are still scraping WA/OR because the **task database** still contains WA/OR tasks. The admin dashboard save was failing due to a path error on Render.

## What I Just Did
✅ Fixed the path error in `store_config.py`
✅ Committed and pushed the fix to GitHub
🔄 Render is now redeploying (takes ~2 minutes)

## What You Need to Do NOW

### Step 1: Wait for Render to Redeploy (2 minutes)
Watch the Render dashboard: https://dashboard.render.com/
- Look for "gloorbot-coordinator" service
- Wait for the status to show "Live" with a green checkmark
- You'll see "Deploy succeeded" in the logs

### Step 2: Save the Florida Configuration
1. Go to the admin dashboard: https://gloorbot-coordinator.onrender.com/admin/dashboard
2. Click the **"Southeast (FL)"** tab
3. Select Florida (it should already be selected)
4. Click the **"🌴 Stuart to Miami (18)"** preset button
5. Click **"Save Configuration"**
6. You should see a success message like:
   ```
   ✅ Configuration saved!
   🗑️ Cleared 10,125 old tasks
   ✨ Created 4,050 new tasks
   Workers will now scrape: FL
   ```

### Step 3: Restart Your Workers
In the Worker GUI:
1. Click **"Kill"** to stop all workers
2. Wait 5 seconds
3. Click **"Join"** to reconnect

### Step 4: Verify Florida is Being Scraped
Watch the worker console logs. You should see lines like:
```
[slot-0] Leased task: Stuart, FL (#1109) - Category: ...
[slot-1] Leased task: West Palm Beach, FL (#1962) - Category: ...
```

If you see **FL** in the logs, it's working! ✅

## If It Still Shows WA/OR After Step 3

Run this command to check what's in the database:
```powershell
python check_coordinator_tasks.py
```

If it shows WA/OR tasks, the save didn't work. Check the Render logs for errors.

## Timeline
- **Now**: Render is redeploying (2 min)
- **+2 min**: Save Florida config
- **+3 min**: Restart workers
- **+4 min**: Workers should be scraping Florida!

## Emergency Contact
If this doesn't work after 5 minutes, check:
1. Render deployment status (must be "Live")
2. Admin dashboard save response (must show "tasks_cleared" and "tasks_inserted")
3. Worker logs (must show "FL" in store names)
