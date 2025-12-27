"""
Test the production version locally
"""

import asyncio
import sys
sys.path.insert(0, 'src')

# Mock Apify Actor
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
        return {
            "testMode": True,
            "maxStores": 2,  # Test with 2 stores
            "maxCategories": 2,  # Test with 2 categories
            "stateFilter": ["WA"]  # Just WA for testing
        }

    @staticmethod
    async def push_data(data):
        print(f"[PUSH] Would push {len(data)} items to dataset")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

# Replace the real Actor with mock
import src.main_production as main_production
main_production.Actor = MockActor()

# Run the main function
asyncio.run(main_production.main())
