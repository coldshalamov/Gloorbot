# 🚀 Run All 49 Stores (WA + OR)

## Complete Coverage: 35 WA + 14 OR = 49 Total Stores

---

## Three Ways to Run

### Option 1: One Command for Everything (Easiest)

```bash
python run_all_stores.py --max-workers 8
```

**What happens:**
1. Runs all 35 WA stores first (6-8 hours)
2. Then runs all 14 OR stores (2-3 hours)
3. Total: **8-11 hours for complete coverage**
4. Products organized by state in separate folders

**Output:**
```
scrape_output_supervised/
├── WA/
│   ├── worker_0_store_0061.jsonl
│   ├── worker_1_store_1089.jsonl
│   └── ... (35 stores)
└── OR/
    ├── worker_0_store_0024.jsonl
    ├── worker_1_store_0117.jsonl
    └── ... (14 stores)
```

### Option 2: Run States Separately (More Control)

**First, run WA:**
```bash
python intelligent_supervisor.py --state WA --max-workers 8
```
*Wait 6-8 hours for completion*

**Then, run OR:**
```bash
python intelligent_supervisor.py --state OR --max-workers 8
```
*Wait 2-3 hours for completion*

**Why separate?** Better control if you need to pause between states.

### Option 3: Run States in Parallel (Advanced)

**Terminal 1 - WA:**
```bash
python intelligent_supervisor.py --state WA --max-workers 4
```

**Terminal 2 - OR:**
```bash
python intelligent_supervisor.py --state OR --max-workers 4
```

**⚠️ Important:** Reduce `--max-workers` to 4 each so you don't exceed system resources (8 total workers across both).

---

## Expected Results

### By State

| State | Stores | Categories | Expected Products | Runtime |
|-------|--------|------------|-------------------|---------|
| WA    | 35     | 515        | 15,000-25,000    | 6-8 hrs |
| OR    | 14     | 515        | 6,000-10,000     | 2-3 hrs |
| **Total** | **49** | **515** | **21,000-35,000** | **8-11 hrs** |

### By Hardware

| Your RAM | Workers/State | Total Runtime |
|----------|---------------|---------------|
| 8GB      | 3-4           | 14-18 hours   |
| 16GB     | 6-8           | 8-11 hours    |
| 32GB     | 10-15         | 5-7 hours     |

---

## Monitoring Progress

### Monitor Both States (Option 1)

When using `run_all_stores.py`, the supervisor automatically switches between WA and OR status files.

**Check current state:**
```bash
# For WA (during Phase 1):
python check_supervisor_status.py

# The status file location auto-switches to WA/supervisor_status.json
```

### Monitor Specific State (Options 2 & 3)

**For WA:**
```bash
cat scrape_output_supervised/WA/supervisor_status.json | python -m json.tool
```

**For OR:**
```bash
cat scrape_output_supervised/OR/supervisor_status.json | python -m json.tool
```

### Live Monitoring Script

I'll create one for you that auto-detects which state is running:

```bash
python monitor_all_states.py --watch
```

---

## After Completion

### Merge All Products

**Combine WA + OR:**
```bash
cat scrape_output_supervised/WA/worker_*.jsonl scrape_output_supervised/OR/worker_*.jsonl > products_all_49_stores.jsonl
```

**Check total count:**
```bash
wc -l products_all_49_stores.jsonl
```

### Analyze Redundancy

```bash
python analyze_url_redundancy.py products_all_49_stores.jsonl
```

**You get:**
- `URLS_TO_REMOVE.txt` - redundant categories across both states
- Coverage analysis
- Optimization recommendations

### Optimize & Re-run

```bash
# Edit LowesMap.txt to remove redundant URLs
# Then run optimized scrape:
python run_all_stores.py --max-workers 8
```

---

## Timeline Example (16GB RAM, 8 workers max)

```
00:00 - Start WA Phase
00:01 - Worker 0: Arlington, WA (#0061) starts
01:00 - Workers scaled to 3
02:00 - Workers scaled to 6
03:00 - Workers at max (8)
06:00 - WA store completions begin
07:30 - All WA stores complete (18,500 products)

07:31 - Start OR Phase
07:32 - Worker 0: Bend, OR (#0024) starts
08:30 - Workers scaled to 6
09:30 - OR store completions begin
10:45 - All OR stores complete (7,800 products)

TOTAL: 10:45 runtime, 26,300 products, 49 stores ✅
```

---

## Quick Decision Guide

**Choose Option 1 (run_all_stores.py) if:**
- ✅ You want to start it and walk away
- ✅ You don't need to pause between states
- ✅ You want cleanly organized output by state

**Choose Option 2 (separate commands) if:**
- ✅ You want to review WA results before starting OR
- ✅ You want to adjust parameters between states
- ✅ You might need to pause overnight between states

**Choose Option 3 (parallel) if:**
- ✅ You have 16GB+ RAM
- ✅ You want maximum speed
- ✅ You're comfortable managing two terminals

---

## The Simplest Command

**Just run this and come back in 8-11 hours:**

```bash
cd C:\Users\User\Documents\GitHub\Telomere\Gloorbot
python run_all_stores.py --max-workers 8
```

**That's it.** The system handles:
- Starting conservatively
- Scaling intelligently
- Detecting blocking
- Switching from WA to OR
- Completing all 49 stores
- Organizing output by state

---

## Summary

| Approach | Command | Runtime | Control |
|----------|---------|---------|---------|
| **All-in-One** | `python run_all_stores.py --max-workers 8` | 8-11 hrs | Low (automated) |
| **Sequential** | Two separate `intelligent_supervisor.py` calls | 8-11 hrs | Medium (pause between) |
| **Parallel** | Two terminals simultaneously | 6-9 hrs | High (manual) |

**Recommended:** All-in-One for first run, then use Sequential if you want more control.

🎯 **Your command:** `python run_all_stores.py --max-workers 8`
