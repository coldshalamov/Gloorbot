"""
Run scraper for a SINGLE specific store (for parallel orchestrator)
Usage: python run_single_store.py --store-id 0061 --state WA --output worker_0.jsonl
"""

import asyncio
import argparse
import sys
from pathlib import Path
sys.path.insert(0, 'apify_actor_seed/src')

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
        parser.add_argument('--categories', type=int, default=515, help='Max categories')
        args = parser.parse_args()

        self.output_file = args.output
        self.store_id_filter = args.store_id

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
parser.add_argument('--categories', type=int, default=515)
args, _ = parser.parse_known_args()

# Create mock with output file
mock_actor = MockActor(args.output)

# Replace Actor with mock
import main
main.Actor = mock_actor

# Modify load_stores_and_categories to filter by store ID
original_load = main.load_stores_and_categories

def filtered_load():
    stores, categories = original_load()
    # Filter to only the requested store
    stores = [s for s in stores if s['store_id'] == args.store_id]
    if not stores:
        print(f"[ERROR] Store {args.store_id} not found in LowesMap.txt")
        sys.exit(1)
    print(f"[INFO] Filtered to store: {stores[0]['name']}")
    return stores, categories

main.load_stores_and_categories = filtered_load

# Run
asyncio.run(main.main())
