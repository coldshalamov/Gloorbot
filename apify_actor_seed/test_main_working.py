"""
Quick test of main_working.py locally (without Apify SDK overhead)
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
    async def get_input():
        return {"testMode": True, "maxCategories": 2}

    @staticmethod
    async def push_data(data):
        print(f"[PUSH] Would push {len(data)} items to dataset")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

# Replace the real Actor with mock
import src.main_working as main_working
main_working.Actor = MockActor()

# Run the main function
asyncio.run(main_working.main())
