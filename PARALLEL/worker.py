"""
Run scraper for a SINGLE specific store (for parallel orchestrator)
Usage: python worker.py --store-id 0061 --state WA --output output/store_0061.jsonl
"""

import asyncio
import argparse
import sys
from pathlib import Path

class MockActor:
    def __init__(self, output_file):
        self.output_file = output_file

    class log:
        @staticmethod
        def info(msg):
            print(f"[INFO] {msg}", flush=True)
        @staticmethod
        def error(msg):
            print(f"[ERROR] {msg}", flush=True)
        @staticmethod
        def warning(msg):
            print(f"[WARNING] {msg}", flush=True)

    async def get_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--store-id', required=True, help='Specific store ID to scrape')
        parser.add_argument('--state', default='WA', help='State filter')
        parser.add_argument('--output', required=True, help='Output JSONL file')
        parser.add_argument('--categories', type=int, default=2000, help='Max categories')
        parser.add_argument('--start-idx', type=int, default=0, help='Category index to start from')
        parser.add_argument('--check-file', help='File to save current progress index')
        args = parser.parse_args()

        self.output_file = args.output
        self.store_id_filter = args.store_id
        self.start_idx = args.start_idx
        self.check_file = args.check_file

        return {
            "testMode": False,
            "maxStores": 99999,  # Will be filtered by store_id
            "maxCategories": args.categories,
            "stateFilter": [args.state],
            "storeIdFilter": args.store_id  # Custom filter
        }

    async def push_data(self, data):
        import json

        # Write to worker-specific output file
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "a") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        print(f"[PUSH] Saved {len(data)} products to {self.output_file}", flush=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

# Parse args early to create properly configured mock
parser = argparse.ArgumentParser()
parser.add_argument('--store-id', required=True)
parser.add_argument('--state', default='WA')
parser.add_argument('--output', required=True)
parser.add_argument('--categories', type=int, default=2000)
parser.add_argument('--start-idx', type=int, default=0)
parser.add_argument('--check-file')
args, _ = parser.parse_known_args()

# Create mock with output file
mock_actor = MockActor(args.output)
mock_actor.start_idx = args.start_idx
mock_actor.check_file = args.check_file

# Replace Actor with mock - import from local scraper.py
import scraper
scraper.Actor = mock_actor

# Modify load_stores_and_categories to filter by store ID and apply start index
original_load = scraper.load_stores_and_categories

def filtered_load():
    stores, categories = original_load()
    # Filter to only the requested store
    stores = [s for s in stores if s['store_id'] == args.store_id]
    if not stores:
        print(f"[ERROR] Store {args.store_id} not found in urls.txt")
        sys.exit(1)
    
    # Apply category start index by trimming the list
    if args.start_idx > 0:
        print(f"[INFO] Resuming from category index {args.start_idx}")
        categories = categories[args.start_idx:]
    
    print(f"[INFO] Filtered to store: {stores[0]['name']}")
    return stores, categories

scraper.load_stores_and_categories = filtered_load

# Monkeypatch main loop to track progress
original_main = scraper.main
async def tracked_main():
    # We need to wrap the internal category loop in scraper.py
    # Since scraper.py loop is inside async main(), we patch the scrape_category_all_pages
    original_scrape = scraper.scrape_category_all_pages
    
    # We track our global offset
    current_offset = args.start_idx

    async def wrapped_scrape(page, category_url, store_info):
        nonlocal current_offset
        res = await original_scrape(page, category_url, store_info)
        
        # After each category, update checkpoint
        current_offset += 1
        if mock_actor.check_file:
            try:
                with open(mock_actor.check_file, 'w') as f:
                    f.write(str(current_offset))
                print(f"[PROGRESS] Updated checkpoint to {current_offset}", flush=True)
            except:
                pass
        return res

    scraper.scrape_category_all_pages = wrapped_scrape
    return await original_main()

# Run
asyncio.run(tracked_main())
