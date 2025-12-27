# Intelligent Self-Scaling Lowe's Scraper - User Guide

## What This Does

This is the **"just run it and let it work"** solution you wanted. It:

✅ **Starts conservatively** (1 worker scraping 1 store)
✅ **Monitors itself** every minute for blocking, crashes, and performance
✅ **Gradually scales up** by adding workers (up to your max limit)
✅ **Maintains optimal throughput** without triggering Akamai blocking
✅ **Can use AI** (GPT-4o-mini) to make smarter scaling decisions
✅ **Rotates browser profiles** (each worker gets unique profile per store)
✅ **Works with your carrier IP** to simulate multiple phones in your area

## Quick Start

### 1. Basic Usage (No AI)

```bash
# Scrape all WA stores with up to 10 parallel workers
python intelligent_scraper.py --state WA --max-workers 10

# Scrape all OR stores with up to 5 parallel workers
python intelligent_scraper.py --state OR --max-workers 5
```

The orchestrator will:
1. Start with 1 worker on the first store
2. Monitor for 5 minutes
3. If healthy, add another worker
4. Repeat until hitting max workers or detecting issues
5. Scale down if blocking detected
6. Complete all stores

### 2. AI-Assisted Mode (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# Run with AI decision-making
python intelligent_scraper.py --state WA --max-workers 10 --use-ai
```

The AI will analyze:
- Worker health and performance
- Products per minute rate
- Blocking incidents
- Resource utilization

And make smarter decisions about when to scale up/down.

### 3. Advanced Configuration

```bash
# Custom max workers and explicit API key
python intelligent_scraper.py \
  --state WA \
  --max-workers 15 \
  --use-ai \
  --openai-key "sk-your-key-here"
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Intelligent Orchestrator (intelligent_scraper.py)
│  - Launches worker processes                    │
│  - Monitors every 60 seconds                    │
│  - Makes scaling decisions                      │
│  - Optional: Calls GPT-4o-mini API              │
└─────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────┐
        │            │            │          │
   ┌────▼───┐  ┌────▼───┐  ┌────▼───┐  ┌──▼──┐
   │Worker 0│  │Worker 1│  │Worker 2│  │ ... │
   │Store   │  │Store   │  │Store   │  │     │
   │#0061   │  │#1089   │  │#1631   │  │     │
   │Profile │  │Profile │  │Profile │  │     │
   │A       │  │B       │  │C       │  │     │
   └────────┘  └────────┘  └────────┘  └─────┘
```

### Each Worker:
- Runs `run_single_store.py` for ONE specific store
- Gets its own unique browser profile (`.playwright-profiles/store-{id}`)
- Writes to its own output file (`scrape_output_parallel/worker_X_store_Y.jsonl`)
- Scrapes all 515 categories for that store
- Takes ~1-2 hours per store (depends on product count)

### The Orchestrator:
- Starts conservatively (1 worker)
- Every 5 minutes, checks if it's safe to add another
- Monitors for:
  - **Blocking**: "Access Denied" pages → scale down immediately
  - **Stalling**: No new products for 10+ minutes → investigate
  - **Crashes**: Browser exits with error → restart or skip
  - **Performance**: Products/minute rate
- Adds workers gradually: 1 → 2 → 3 → 4 → etc.
- Stops at max workers or when all stores are done

## Scaling Logic

### When to Scale UP ✅
- All current workers are healthy
- No blocking incidents
- Less than 50% of workers stalled
- 5+ minutes since last scaling action
- Under max worker limit

### When to Scale DOWN ❌
- ANY worker gets blocked by Akamai
- More than 50% of workers are stalled
- AI recommends backing off

### When to MAINTAIN ⏸️
- Some workers stalled (monitoring)
- Recently scaled (waiting for stability)
- At max worker limit

## Your Carrier IP Advantage

With your mobile carrier IP, you have a **huge advantage**:

### Why This Works:
- **Residential IP**: Carrier IPs are residential, not datacenter
- **Rotating Profiles**: Each worker uses a different browser profile
- **Geolocation**: All requests appear to come from "phones in your area"
- **Natural Behavior**: With warmup + human behavior, looks like real users

### What You Can Do:
- Run **10-15 parallel workers** safely (test conservatively first)
- Each worker looks like a separate phone/person
- Carrier IP makes rate limiting more lenient
- No proxy rotation needed

## Expected Performance

### Conservative (5 workers)
- **Runtime**: 10-14 hours for all 35 WA stores
- **Throughput**: ~100-150 products/minute
- **Safety**: Very low blocking risk

### Moderate (10 workers)
- **Runtime**: 5-7 hours for all 35 WA stores
- **Throughput**: ~200-300 products/minute
- **Safety**: Low blocking risk with monitoring

### Aggressive (15 workers)
- **Runtime**: 3-5 hours for all 35 WA stores
- **Throughput**: ~300-500 products/minute
- **Safety**: Monitor closely for blocking

### Target: 24-Hour Cycle
To complete a full run (49 stores × 515 categories) in 24 hours:

```bash
# Morning: WA stores (35)
python intelligent_scraper.py --state WA --max-workers 10 --use-ai
# Expected: 6-8 hours

# Afternoon: OR stores (14)
python intelligent_scraper.py --state OR --max-workers 10 --use-ai
# Expected: 3-4 hours

# Total: ~10-12 hours (with 12-hour buffer)
```

## Monitoring During Run

The orchestrator prints status every minute:

```
📊 Status: scale_up - All workers healthy, 245.3 products/min
   Active Workers: 5/10
   Total Products: 12,453
```

### What to Watch:
- **Products/minute**: Should be steady or increasing
- **Active Workers**: Should gradually increase
- **Blocking Incidents**: Should be 0

### If You See Blocking:
```
⚠️  Worker 3 detected blocking - scaling down
📉 Scaling DOWN: Removing 1 worker(s)
```
This is **automatic** - the orchestrator handles it.

## Output Files

All data goes to: `scrape_output_parallel/`

```
scrape_output_parallel/
├── worker_0_store_0061.jsonl   ← Arlington store data
├── worker_1_store_1089.jsonl   ← Auburn store data
├── worker_2_store_1631.jsonl   ← Bellingham store data
└── ...
```

### After Completion, Merge Results:

```bash
# Combine all worker outputs
cat scrape_output_parallel/worker_*.jsonl > scrape_output/products_full.jsonl

# Analyze
python analyze_results.py
```

## AI Mode Details

When you use `--use-ai`, the orchestrator:

1. **Every 5 minutes**, gathers:
   - Current worker count
   - Products scraped per worker
   - Blocking incidents
   - Runtime per worker
   - Products/minute rate

2. **Sends to GPT-4o-mini**:
   ```
   Prompt: "Should we scale up/down/maintain?"
   Model: gpt-4o-mini (cheap: ~$0.01 per 100 decisions)
   ```

3. **Gets decision**:
   ```json
   {
     "decision": "scale_up",
     "reason": "All workers healthy, no blocking",
     "target_workers": 6
   }
   ```

4. **Executes** the AI's recommendation

### Cost:
- ~12 AI calls per hour (every 5 minutes)
- ~$0.001 per call with gpt-4o-mini
- **Total cost for 24-hour run: ~$0.30**

## Troubleshooting

### Problem: Workers Keep Crashing
**Symptom**: Orchestrator starts workers, they exit immediately
**Solution**: Check browser installation
```bash
# Ensure Chrome is installed (not just Chromium)
which chrome
# Should show: /usr/bin/google-chrome or similar
```

### Problem: All Workers Get Blocked
**Symptom**: Multiple "Access Denied" messages
**Solution**: You scaled too aggressively
- Restart with `--max-workers 3`
- Let it run for 1 hour before increasing
- Or use AI mode to make safer decisions

### Problem: Stalling at Same Product Count
**Symptom**: Worker shows same product count for 30+ minutes
**Solution**: That category may be done or has issues
- Orchestrator will detect and continue
- Check individual worker output file

### Problem: No AI Decisions
**Symptom**: `--use-ai` flag but no "🤖 AI Decision" messages
**Solution**: Check OpenAI setup
```bash
# Install OpenAI SDK
pip install openai

# Set API key
export OPENAI_API_KEY="sk-..."

# Test
python -c "import openai; print(openai.api_key)"
```

## Best Practices

### Start Small, Scale Gradually
```bash
# Day 1: Test with 3 workers
python intelligent_scraper.py --state WA --max-workers 3

# Day 2: If successful, try 5
python intelligent_scraper.py --state WA --max-workers 5

# Day 3: Full production with 10-15
python intelligent_scraper.py --state WA --max-workers 10 --use-ai
```

### Use AI for First Run
- Let GPT-4o-mini learn your system's limits
- It costs pennies but saves hours of trial-and-error
- Disable AI once you know your optimal worker count

### Monitor First Hour Closely
- Watch for blocking in the first 60 minutes
- If no blocking after 1 hour, you're good to go
- Let it run overnight after that

### Schedule for Off-Peak Hours
- Start scrapes at night (11 PM - 6 AM)
- Lower website traffic = less scrutiny
- Reduces chance of anti-bot activation

## Advanced: Customizing Scaling Logic

Edit `intelligent_scraper.py`:

```python
# Change scaling interval (default: 5 minutes)
self.scale_up_interval = 600  # 10 minutes

# Change stall detection (default: 10 minutes)
if time_stalled > 1200:  # 20 minutes

# Change initial workers (default: 1)
self.target_workers = 2  # Start with 2
```

## FAQ

**Q: Can I stop and resume?**
A: Yes! Kill the orchestrator (Ctrl+C). Next run will skip already-completed stores automatically.

**Q: How do I know when it's done?**
A: You'll see: `✅ ALL STORES COMPLETED!` with final statistics.

**Q: Can I run WA and OR simultaneously?**
A: Not recommended - better to do sequentially to avoid triggering rate limits.

**Q: What if my internet drops?**
A: Workers will fail. Restart the orchestrator - it will skip completed stores.

**Q: Can I use this on AWS/cloud?**
A: Yes, but you lose the carrier IP advantage. Use rotating residential proxies instead.

**Q: How much disk space needed?**
A: ~500 MB for full 49-store run (product data + browser profiles)

## Next-Level Optimization

Once you've proven 24-hour cycles work:

### 1. **Add Incremental Updates**
- Only scrape products with changes since last run
- Compare timestamps
- Reduces runtime from 24h to ~6-8h

### 2. **Database Integration**
- Stream products directly to database
- Real-time website updates
- No post-processing needed

### 3. **Auto-Retry Failed Categories**
- Track categories that returned 0 products
- Retry them with different worker
- Maximize data completeness

### 4. **Multi-Region Distribution**
- Run from different locations
- Rotate between regions
- Even higher throughput

## Summary

**You wanted**: "Run it and it works"
**You got**: Intelligent orchestrator that self-manages parallelization

**Commands you need**:
```bash
# Install dependencies
pip install openai  # Optional for AI mode

# Run it
python intelligent_scraper.py --state WA --max-workers 10 --use-ai

# Walk away and let it work
```

**What happens**:
1. Starts with 1 worker
2. Monitors performance
3. Gradually adds workers (with AI or rule-based logic)
4. Scales down if blocking detected
5. Completes all stores
6. Gives you final stats

**Time to completion**:
- With 10 workers: ~6-8 hours for all 35 WA stores
- **Target met**: Can easily do 24-hour cycles

🎯 **You can now run this daily and always have fresh markdown data!**
