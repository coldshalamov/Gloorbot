"""
Run a test scrape with specific stores and categories
Usage: python run_test_scrape.py --stores 2 --categories 10
"""

import asyncio
import argparse
import sys
sys.path.insert(0, 'apify_actor_seed/src')

class MockActor:
    class log:
        @staticmethod
        def info(msg):
            print(f"[INFO] {msg}")
        @staticmethod
        def error(msg):
            print(f"[ERROR] {msg}")
        @staticmethod
        def warning(msg):
            print(f"[WARNING] {msg}")

    @staticmethod
    async def get_input():
        parser = argparse.ArgumentParser()
        parser.add_argument('--stores', type=int, default=1)
        parser.add_argument('--categories', type=int, default=5)
        parser.add_argument('--state', default='WA')
        args = parser.parse_args()

        return {
            "testMode": False,
            "maxStores": args.stores,
            "maxCategories": args.categories,
            "stateFilter": [args.state]
        }

    @staticmethod
    async def push_data(data):
        import json
        from pathlib import Path

        output_dir = Path("scrape_output")
        output_dir.mkdir(exist_ok=True)

        # Append to JSONL file
        with open(output_dir / "products.jsonl", "a") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        print(f"[PUSH] Saved {len(data)} products to scrape_output/products.jsonl")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

# Replace Actor with mock
import main
main.Actor = MockActor()

# Run
asyncio.run(main.main())
