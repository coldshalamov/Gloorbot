# Intelligent Supervisor - Your AI Babysitter

## What This Actually Does

This is the **hands-off solution** you wanted:

✅ **Starts conservatively** (1 worker, waits to see if it works)
✅ **Monitors actively** (checks every 60 seconds):
  - Is worker still alive?
  - How many products per minute?
  - Memory and CPU usage
  - Any blocking detected?
  - Is it stalled?

✅ **Makes smart decisions**:
  - "Worker healthy + have resources → add another"
  - "Worker blocked → remove a worker"
  - "Workers stalled → investigate, don't add more"
  - "RAM >70% → don't add more"

✅ **Self-corrects**:
  - Auto-restarts crashed workers
  - Scales down if blocking detected
  - Won't add workers if resources are low

✅ **You can monitor it**:
  - From another terminal
  - Via Claude Code CLI
  - Check status anytime without interrupting

---

## Quick Start

### Terminal 1: Start Supervisor
```bash
cd C:\Users\User\Documents\GitHub\Telomere\Gloorbot
python intelligent_supervisor.py --state WA --max-workers 8 --check-interval 60
```

**What happens**:
```
[12:00:01] [INFO] SUPERVISOR: Intelligent Supervisor Starting
[12:00:01] [INFO] SUPERVISOR: State: WA
[12:00:01] [INFO] SUPERVISOR: Max Workers: 8
[12:00:01] [INFO] SUPERVISOR: Check Interval: 60s
[12:00:01] [INFO] SUPERVISOR: Loaded 35 WA stores
[12:00:02] [INFO] Worker 0: Starting for Arlington, WA (#0061)
[12:00:05] [INFO] Worker 0: Started with PID 12345

--- Iteration 1 ---
[12:01:05] [INFO] Worker 0: Health: 45 products | 0.8/min | 856MB | 12.3% CPU
[12:01:05] [INFO] SUPERVISOR: Resources: RAM 856/11200MB | CPU 12.3/80.0%
[12:01:05] [INFO] SUPERVISOR: Decision: scale_up - All workers healthy, RAM: 10344MB free, CPU: 67.7% free
[12:01:06] [INFO] Worker 1: Starting for Auburn, WA (#1089)

--- Iteration 2 ---
[12:02:05] [INFO] Worker 0: Health: 98 products | 0.9/min | 892MB | 11.8% CPU
[12:02:05] [INFO] Worker 1: Health: 42 products | 0.7/min | 834MB | 10.2% CPU
[12:02:05] [INFO] SUPERVISOR: Resources: RAM 1726/11200MB | CPU 22.0/80.0%
[12:02:05] [INFO] SUPERVISOR: Decision: scale_up - All workers healthy, RAM: 9474MB free, CPU: 58.0% free
...
```

### Terminal 2: Monitor Status
```bash
# One-time check:
python check_supervisor_status.py

# Continuous monitoring:
python check_supervisor_status.py --watch
```

**You see**:
```
======================================================================
SUPERVISOR STATUS
======================================================================
Last Update: 5s ago
Uptime: 12.3m

📊 STATISTICS
  Total Products: 1,247
  Workers Launched: 3
  Current Workers: 3
  Failed/Restarted: 0
  Blocking Incidents: 0

  Rate: 6,085 products/hour

👷 WORKERS
  Active: 3/3

  ✅ Worker 0: Arlington, WA (#0061)
     Products: 542 (0.9/min)
     Resources: 892MB RAM, 11.8% CPU

  ✅ Worker 1: Auburn, WA (#1089)
     Products: 423 (0.8/min)
     Resources: 834MB RAM, 10.2% CPU

  ✅ Worker 2: Bellingham, WA (#1631)
     Products: 282 (0.7/min)
     Resources: 801MB RAM, 9.5% CPU

🏥 HEALTH
  ✅ All systems normal

======================================================================

💡 Commands:
  Watch live: python check_supervisor_status.py --watch
  View logs: tail -f scrape_output_supervised/supervisor.log
  Stop: Ctrl+C in supervisor terminal
```

---

## How It Makes Decisions

### Every 60 seconds, the supervisor:

1. **Checks each worker**:
   - Still running?
   - How many products scraped?
   - Products/minute rate
   - Memory usage
   - CPU usage

2. **Analyzes system resources**:
   ```
   Total RAM used by all workers: 2.1GB
   Max allowed (70% of 16GB): 11.2GB
   Available for new worker: 9.1GB ✅

   Total CPU used: 32%
   Max allowed: 80%
   Available: 48% ✅
   ```

3. **Makes decision**:
   ```python
   if any_worker_blocked:
       → Remove most recent worker (scale down)

   elif more_than_half_stalled:
       → Don't add more, investigate current workers

   elif have_resources and all_healthy and under_max:
       → Add another worker (scale up)

   else:
       → Maintain current level
   ```

4. **Executes decision** and logs it

---

## Decision Examples

### Scenario 1: Happy Path (Scaling Up)
```
[12:01:05] Worker 0: Health: 45 products | 0.8/min | 856MB | 12.3% CPU
[12:01:05] Resources: RAM 856/11200MB | CPU 12.3/80.0%
[12:01:05] Decision: scale_up - All workers healthy, RAM: 10344MB free
[12:01:06] Worker 1: Starting for Auburn, WA (#1089)
```

✅ Worker is healthy (producing products)
✅ Have plenty of RAM and CPU
→ **Add another worker**

### Scenario 2: Blocking Detected
```
[12:15:32] Worker 2: Health: 234 products | 0.0/min | 901MB | 8.2% CPU
[12:15:32] Worker 2: STALLED for 10.2 minutes
[12:15:32] Decision: scale_down - Blocking detected in 1 worker(s)
[12:15:33] Worker 2: Stopping...
```

❌ Worker stopped producing products (blocking?)
→ **Remove worker, let others continue**

### Scenario 3: Resource Constrained
```
[12:22:17] Worker 0: Health: 1,245 products | 0.9/min | 1,823MB | 18.3% CPU
[12:22:17] Worker 1: Health: 987 products | 0.8/min | 1,654MB | 16.2% CPU
[12:22:17] Worker 2: Health: 876 products | 0.7/min | 1,512MB | 14.8% CPU
[12:22:17] Worker 3: Health: 734 products | 0.7/min | 1,489MB | 14.1% CPU
[12:22:17] Resources: RAM 6478/8000MB | CPU 63.4/80.0%
[12:22:17] Decision: maintain - Not enough RAM for another worker
```

⚠️ Using 81% of available RAM (6.5GB of 8GB)
→ **Don't add more, maintain current 4 workers**

---

## Parameters You Can Tune

### `--check-interval` (default: 60)
How often to check workers (in seconds)

**Lower (30)**: More responsive, catches issues faster
**Higher (120)**: Less overhead, gives workers more time

**Recommended**: 60 seconds for production

### `--max-workers` (default: 10)
Maximum workers to spawn

**Important**: This is a CEILING, not a target
- Supervisor won't exceed this even if resources allow
- But will stay below if resources don't allow

**Find your limit**:
```bash
# Start conservative:
python intelligent_supervisor.py --state WA --max-workers 5

# If that works well for hours, try:
python intelligent_supervisor.py --state WA --max-workers 8

# Never go higher than your RAM allows:
# 8GB RAM → max 3-4 workers
# 16GB RAM → max 6-10 workers
# 32GB RAM → max 12-15 workers
```

---

## Monitoring from Claude Code

You can have Claude Code check on the supervisor for you:

```bash
# In Claude Code terminal:
python check_supervisor_status.py

# Or for continuous monitoring:
python check_supervisor_status.py --watch
```

**Then you can ask Claude**:
- "How's the supervisor doing?"
- "Any workers stalled?"
- "What's the current rate?"
- "Should I adjust anything?"

Claude will read the status and advise you.

---

## What Gets Logged

### Main Supervisor Log
**File**: `scrape_output_supervised/supervisor.log`

Contains:
- When workers start/stop
- Health checks every 60s
- Decisions made (scale up/down/maintain)
- Resource usage
- Blocking incidents

### Per-Worker Logs
**File**: `scrape_output_supervised/worker_N_supervisor.log`

Contains:
- Worker-specific health data
- Products scraped
- Errors encountered

### Status File (for monitoring)
**File**: `scrape_output_supervised/supervisor_status.json`

Updated every check interval with:
```json
{
  "timestamp": "2025-12-26T12:22:17",
  "uptime_seconds": 735,
  "stats": {
    "total_products": 3842,
    "workers_launched": 4,
    "current_workers": 4,
    "blocking_incidents": 0
  },
  "workers": [
    {
      "id": 0,
      "store": "Arlington, WA (#0061)",
      "alive": true,
      "products": 1245,
      "products_per_min": 0.9,
      "memory_mb": 1823,
      "cpu_percent": 18.3
    },
    ...
  ]
}
```

---

## Typical Run Timeline

### First 5 Minutes (Startup)
```
00:00 - Supervisor starts
00:01 - Worker 0 launches (Arlington)
00:02 - Worker 0 warming up (homepage, store setting)
00:05 - Worker 0 starts producing products
01:00 - First health check: Worker 0 healthy
01:05 - Decision: Add Worker 1 (Auburn)
```

### 5-30 Minutes (Scaling Up)
```
02:05 - Worker 1 healthy, add Worker 2
03:05 - Workers 1-2 healthy, add Worker 3
04:05 - Workers 1-3 healthy, add Worker 4
05:05 - RAM at 70%, maintain at 4 workers
```

### 30+ Minutes (Steady State)
```
06:05 - All 4 workers producing steadily
07:05 - Worker 2 stalls (category finished)
08:05 - Worker 2 starts next category
09:05 - All workers still healthy
10:05 - Worker 0 completes (all categories done)
...
```

### Completion
```
4-8 hours: All workers complete
Final stats: 15,000-25,000 products from 4-8 stores
```

---

## Troubleshooting

### "Supervisor keeps scaling down"
**Symptom**: Workers get removed soon after being added

**Likely cause**: Blocking is happening

**Fix**:
1. Run diagnostic mode on that store
2. Check if "Pickup Today" filter is working
3. Verify no "Access Denied" in browser
4. Try lower max workers (--max-workers 3)

### "Supervisor not adding workers"
**Symptom**: Stuck at 1-2 workers, won't scale up

**Likely cause**: Resource limits or workers appear unhealthy

**Check**:
```bash
python check_supervisor_status.py
```

Look for:
- High RAM/CPU usage
- Workers with 0.0 products/min (stalled)
- Recent blocking incidents

**Fix**: Wait for workers to stabilize, or lower max workers

### "Worker stalled at same product count"
**Symptom**: Worker shows same count for 10+ minutes

**Likely cause**: Large category, or category finished

**Action**: Supervisor will detect this automatically
- If >50% workers stalled → won't add more
- If specific worker stalled 30+ min → may restart it

### "Can't see what's happening in browser"
**Symptom**: Want to see actual browser activity

**Fix**: Workers run `headless=False`, so browsers ARE visible
- Look for Chrome windows with Lowe's website
- Each worker = separate Chrome window
- Watch them scrape in real-time

---

## Advanced: Combining with Diagnostic Mode

For maximum confidence:

### Step 1: Run Diagnostic First
```bash
python diagnostic_scraper.py --store-id 0061 --category-url "https://www.lowes.com/pl/9-volt-batteries-Batteries-Electrical/2858764984"
```

Check `diagnostic_output/` screenshots - everything good?

### Step 2: Start Supervisor
```bash
python intelligent_supervisor.py --state WA --max-workers 8
```

### Step 3: Monitor from Another Terminal
```bash
python check_supervisor_status.py --watch
```

### Step 4: Let It Run
Walk away. Check back in 1 hour.

If status shows:
- ✅ All workers healthy
- ✅ No blocking incidents
- ✅ Good products/min rate

→ It's working! Let it finish.

---

## Comparison to Original Orchestrator

| Feature | Original | Supervisor |
|---------|----------|------------|
| **Starts conservatively** | ✅ | ✅ |
| **Monitors workers** | Basic | Deep (RAM, CPU, products/min) |
| **Resource checking** | ❌ | ✅ (RAM/CPU limits) |
| **Auto-restart failed** | ❌ | ✅ |
| **External monitoring** | ❌ | ✅ (status file) |
| **Detailed logging** | Basic | Per-worker + supervisor |
| **Blocking detection** | Basic | Advanced |
| **Stall detection** | Time-based | Rate-based |

**Bottom line**: Supervisor is smarter, safer, and gives you visibility.

---

## Summary

### You Run:
```bash
python intelligent_supervisor.py --state WA --max-workers 8
```

### It Does:
1. ✅ Starts 1 worker
2. ✅ Watches it for 60 seconds
3. ✅ Checks: healthy? Have resources?
4. ✅ Adds another if yes
5. ✅ Repeats until max workers or resources exhausted
6. ✅ Auto-scales down if blocking
7. ✅ Completes all stores

### You Monitor (optional):
```bash
python check_supervisor_status.py --watch
```

### You Get:
- 4-8 workers running simultaneously (your hardware limit)
- 6-12 hour runtime for full WA state
- 15,000-25,000 products collected
- Automatic handling of issues
- Detailed logs of everything

**This is the "just run it and it works" solution you wanted.**
