# 🤖 AI Supervisor - True Intelligent Monitoring

## What This Actually Does

**The difference:**

| Feature | Regular Supervisor | AI Supervisor |
|---------|-------------------|---------------|
| Monitors metrics | ✅ (RAM, CPU, products/min) | ✅ |
| Rule-based decisions | ✅ ("if RAM > 70%...") | ✅ |
| **AI analyzes logs** | ❌ | ✅ GPT-4o-mini reads logs |
| **AI understands issues** | ❌ | ✅ "Worker stuck on CAPTCHA" |
| **Intelligent recommendations** | ❌ | ✅ "Scale down worker 3, it's blocked" |
| **Written reports** | ❌ | ✅ Analysis saved to JSON |

**Cost:** ~$0.01-0.05 per analysis (GPT-4o-mini is very cheap)

---

## Setup (One-Time)

### Step 1: Install OpenAI Library
```bash
pip install openai
```

### Step 2: Set Your API Key

**Windows:**
```bash
set OPENAI_API_KEY=sk-your-key-here
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY=sk-your-key-here
```

**Or create a `.env` file:**
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

Then install python-dotenv:
```bash
pip install python-dotenv
```

---

## Usage

### Option 1: AI Supervision for All 49 Stores
```bash
python ai_supervisor.py --all-states --max-workers 8
```

**What happens:**
1. Starts intelligent_supervisor.py for WA (35 stores)
2. **AI checks logs every 5 minutes** using GPT-4o-mini
3. AI analyzes: "Are workers healthy? Any blocking? Should we scale?"
4. Saves analysis to `ai_analysis_WA.json`
5. When WA completes, repeats for OR (14 stores)

### Option 2: AI Supervision for Single State
```bash
# WA only:
python ai_supervisor.py --state WA --max-workers 8

# OR only:
python ai_supervisor.py --state OR --max-workers 8
```

### Option 3: Custom Check Interval
```bash
# Check every 10 minutes (less frequent, cheaper):
python ai_supervisor.py --all-states --max-workers 8 --check-interval 600

# Check every 3 minutes (more responsive, more expensive):
python ai_supervisor.py --all-states --max-workers 8 --check-interval 180
```

### Option 4: Different AI Model
```bash
# Use GPT-4 (more expensive but smarter):
python ai_supervisor.py --all-states --max-workers 8 --model gpt-4

# Use GPT-3.5-turbo (cheapest):
python ai_supervisor.py --all-states --max-workers 8 --model gpt-3.5-turbo
```

---

## What AI Analyzes

Every check interval (default 5 minutes), the AI:

1. **Reads supervisor status:**
   - Total products scraped
   - Active workers
   - Workers launched
   - Blocking incidents
   - Resource usage

2. **Reads recent logs:**
   - Last 20 lines of supervisor.log
   - Worker health checks
   - Scaling decisions
   - Errors/warnings

3. **Provides analysis:**
   ```json
   {
     "healthy": true,
     "issues": ["Worker 3 appears stalled - no products for 8 minutes"],
     "recommendation": "investigate",
     "reasoning": "Most workers producing normally, but Worker 3 needs attention",
     "next_check_in": 5
   }
   ```

4. **Saves to file:** `ai_analysis_WA.json` or `ai_analysis_OR.json`

---

## Example AI Analysis Session

### Check #1 (5 minutes in)
```
[2025-12-26 14:05:00] AI Recommendation: scale_up
[2025-12-26 14:05:00] Reasoning: All workers healthy, RAM usage at 35%, CPU at 28%. System can handle more workers.
```

### Check #2 (10 minutes in)
```
[2025-12-26 14:10:00] AI Recommendation: maintain
[2025-12-26 14:10:00] Reasoning: Workers performing well. RAM approaching 60%, wait before adding more.
```

### Check #3 (15 minutes in)
```
[2025-12-26 14:15:00] Issues detected: Worker 4 shows 0.0 products/min for 8 minutes
[2025-12-26 14:15:00] AI Recommendation: investigate
[2025-12-26 14:15:00] Reasoning: Worker 4 may be blocked or stuck. Other workers normal. Suggest checking Worker 4 logs.
```

---

## Cost Estimate

**Per AI check:**
- Input: ~500-800 tokens (status + logs)
- Output: ~150-200 tokens (analysis)
- Total: ~1,000 tokens per check

**GPT-4o-mini pricing (as of Dec 2024):**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- **Cost per check: ~$0.0002 (basically free)**

**For 8-hour run with 5-minute intervals:**
- Total checks: 96 (8 hours × 12 checks/hour)
- Total cost: **$0.02** for entire WA state
- Both WA + OR: **$0.03-0.04 total**

**Negligible cost for massive insight!**

---

## Monitoring AI Supervisor

### View AI Analysis Log
```bash
# WA AI supervisor log:
tail -f ai_supervisor_WA.log

# OR AI supervisor log:
tail -f ai_supervisor_OR.log
```

### View AI Analysis History
```bash
# See all AI analyses for WA:
cat ai_analysis_WA.json | python -m json.tool

# See all AI analyses for OR:
cat ai_analysis_OR.json | python -m json.tool
```

### Example Analysis History
```json
[
  {
    "timestamp": "2025-12-26T14:05:00",
    "iteration": 1,
    "analysis": {
      "healthy": true,
      "issues": [],
      "recommendation": "scale_up",
      "reasoning": "All workers healthy, system has capacity"
    },
    "stats": {
      "total_products": 234,
      "current_workers": 2
    }
  },
  {
    "timestamp": "2025-12-26T14:10:00",
    "iteration": 2,
    "analysis": {
      "healthy": true,
      "issues": [],
      "recommendation": "maintain",
      "reasoning": "RAM approaching limit"
    },
    "stats": {
      "total_products": 567,
      "current_workers": 4
    }
  }
]
```

---

## Comparison: Regular vs AI Supervisor

### Regular Supervisor (`intelligent_supervisor.py`)
```bash
python run_all_stores.py --max-workers 8
```

**Pros:**
- No API costs
- No dependencies
- Fast decisions (every 60s)

**Cons:**
- Rule-based only
- Can't understand complex issues
- No written analysis

**Best for:** Normal operation, proven setups

### AI Supervisor (`ai_supervisor.py`)
```bash
python ai_supervisor.py --all-states --max-workers 8
```

**Pros:**
- True intelligence
- Understands nuanced issues
- Provides written analysis
- Can catch edge cases

**Cons:**
- Requires OpenAI API key
- ~$0.04 cost for full run
- Slightly slower (5min intervals)

**Best for:** First runs, debugging, learning patterns

---

## Recommended Workflow

### First Time Running
```bash
# Use AI supervisor to learn what works:
python ai_supervisor.py --state WA --max-workers 8
```

**After completion:**
- Review `ai_analysis_WA.json` for insights
- See what issues AI caught
- Learn your optimal worker count

### Production Runs
```bash
# Use regular supervisor (proven and free):
python run_all_stores.py --max-workers 8
```

**Switch to AI supervisor if:**
- Something seems wrong
- Need to debug an issue
- Want detailed analysis

---

## Advanced: AI Screenshot Analysis (Future)

**Current:** AI only reads text logs
**Possible:** AI could analyze screenshots

To enable (requires updates):
1. Take screenshots at intervals
2. Send to GPT-4 Vision
3. AI analyzes: "I see a CAPTCHA", "Store context not set", etc.

Cost would increase to ~$0.10-0.20 per run (still very cheap).

---

## Summary

| Run This | When | Cost | Intelligence Level |
|----------|------|------|--------------------|
| `python run_all_stores.py --max-workers 8` | Normal production | $0 | Rule-based (smart rules) |
| `python ai_supervisor.py --all-states --max-workers 8` | First run, debugging | ~$0.04 | AI-powered analysis |

**Both work great. AI version gives you written insights and catches edge cases.**

---

## Quick Start

```bash
# One-time setup:
pip install openai
set OPENAI_API_KEY=sk-your-key-here

# Run with AI supervision:
python ai_supervisor.py --all-states --max-workers 8

# Monitor AI decisions:
tail -f ai_supervisor_WA.log

# Review AI analysis after:
cat ai_analysis_WA.json | python -m json.tool
```

**You now have true AI babysitting your scraper!** 🤖
