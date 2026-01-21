# How Configuration Changes Work Now

## The Problem (Before)
When you changed the configuration on the website from "Oregon/Washington" to "Southeast Florida", the scraper kept scraping Oregon/Washington because:
1. The backend had a bug that prevented saving
2. The coordinator only loaded tasks once at startup
3. Workers kept getting assigned old tasks even after you "killed" them

## The Solution (Now)

### What Happens When You Click "Save"
1. **Backend clears ALL old tasks** from the coordinator database
2. **Backend creates NEW tasks** based on your selection (e.g., Florida stores)
3. **Workers immediately stop getting old tasks** (because they're deleted)
4. **Workers start getting new tasks** (Florida stores) on their next request
5. **You see a confirmation** showing exactly how many tasks were cleared and created

### The Worker GUI "Kill → Join" Cycle

**When you click "Kill":**
- The worker stops processing its current task
- It disconnects from the coordinator
- All Chrome windows close

**When you click "Join" again:**
- The worker reconnects to the coordinator
- It requests a NEW task from the coordinator
- The coordinator assigns it a task from the **current** configuration
- If you changed to Florida, it will get a Florida task

### How to Verify It's Working

#### Option 1: Check the Admin Dashboard Toast
After clicking "Save", you'll see a message like:
```
✅ Configuration saved!
🗑️ Cleared 10,125 old tasks
✨ Created 4,050 new tasks
Workers will now scrape: FL
```

This confirms the database was updated.

#### Option 2: Run the Diagnostic Script
```powershell
python check_coordinator_tasks.py
```

This shows you exactly what's in the coordinator database:
```
📦 Total Tasks: 4,050

📍 Tasks by State:
   FL: 4,050 tasks

🏪 Top 10 Stores (by task count):
   Stuart, FL (#1109): 225 tasks
   West Palm Beach, FL (#1962): 225 tasks
   ...
```

#### Option 3: Watch the Worker Logs
When a worker starts, it logs which store it's scraping:
```
[slot_0] Leased task: Stuart, FL (#1109) - Category: Clearance
```

If you see Florida stores, it's working!

## Step-by-Step: Switching from WA/OR to FL

1. **Open the Admin Dashboard** (http://localhost:8000/admin/dashboard)
2. **Click the "Southeast (FL)" tab**
3. **Click the Florida 🌴 card** to select it
4. **(Optional) Select specific stores** or use the "Stuart to Miami" preset
5. **Click "Save Configuration"**
6. **Wait for the success message** showing tasks cleared/created
7. **In the Worker GUI, click "Kill"** to stop current work
8. **Click "Join"** to reconnect
9. **Watch the worker logs** - you should see Florida stores being scraped

## Finishing the Current Store

The worker will **NOT** finish the current store if you kill it. It will:
- Stop immediately when you click "Kill"
- Abandon the current task (the coordinator will reassign it to another worker later)
- Start fresh with a new task when you click "Join"

If you want workers to finish their current task before switching:
- **Don't click "Kill"**
- Just save the new configuration
- Workers will finish their current task, then request a new one
- The new task will be from the updated configuration (Florida)

## Troubleshooting

### "I saved FL config but workers are still scraping WA/OR"
1. Run `python check_coordinator_tasks.py` to verify the database
2. If it shows WA/OR tasks, the save didn't work - check the coordinator logs
3. If it shows FL tasks, click "Kill" then "Join" in the worker GUI

### "Workers aren't getting any tasks"
1. Check that the coordinator server is running
2. Run `python check_coordinator_tasks.py` - if it shows 0 tasks, save a configuration
3. Check the worker logs for connection errors

### "I want to switch back to WA/OR"
1. Click the "Northwest (WA/OR)" tab
2. Select WA and/or OR
3. Click "Save Configuration"
4. Kill and rejoin workers (or let them finish current task)

## Real-Time vs. Finish-Current-Store

**Real-Time (Immediate):**
- Click "Save" → "Kill" → "Join"
- Workers immediately start on new region
- Current task is abandoned (will be reassigned)

**Finish-Current-Store (Graceful):**
- Click "Save" only
- Workers finish their current task (might take 5-15 minutes)
- Next task they request will be from the new configuration
- No tasks are abandoned
