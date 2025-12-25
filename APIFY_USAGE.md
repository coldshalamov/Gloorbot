# How to Run Apify Actors

## For Codex: Just Run These Commands

The API credentials are already embedded in the scripts below. Just execute them.

### Method 1: Python Script (Recommended)

```bash
# List all actors
python apify_helper.py list

# Run the lowes-cheapskate actor
python apify_helper.py run lowes-cheapskate '{"stores":[{"store_id":"0004"}],"categories":[{"name":"Clearance","url":"https://www.lowes.com/pl/The-back-aisle/2021454685607"}],"max_pages_per_category":2}'

# Check status
python apify_helper.py status RUN_ID

# Get results
python apify_helper.py results RUN_ID
```

### Method 2: Bash Script

```bash
# Make executable
chmod +x run_apify_actor.sh

# Run with default settings
./run_apify_actor.sh

# Run specific actor
./run_apify_actor.sh lowes-cheapskate input.json
```

### Method 3: Windows Batch

```cmd
run_apify_actor.bat lowes-cheapskate input.json
```

## Quick Test

Run this to test everything works:

```bash
python apify_helper.py list
```

This should show your 4 actors without any errors.

## For Long-Running Actors

The Python script will automatically monitor progress and download results when complete.

## Input File Format

Create `input.json`:

```json
{
  "stores": [
    {"store_id": "0004", "name": "Rainier", "city": "Seattle", "state": "WA", "zip": "98144"}
  ],
  "categories": [
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}
  ],
  "max_pages_per_category": 2
}
```

Then run:

```bash
python apify_helper.py run lowes-cheapskate input.json
```

## Results

Results are saved to `results_<RUN_ID>.json` automatically.
