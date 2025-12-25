"""
Test the actual Apify actor locally with full anti-fingerprinting
"""
import asyncio
import sys
import os

# Fix Windows console encoding
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')

# Set test input
os.environ['APIFY_INPUT_KEY'] = 'INPUT'
os.environ['APIFY_DEFAULT_KEY_VALUE_STORE_ID'] = 'default'
os.environ['APIFY_DEFAULT_DATASET_ID'] = 'default'

# Create test input
test_input = {
    "maxPages": 1,  # Just test 1 page
    "zipCode": "98101",  # Seattle
    "storeId": "1856",
    "proxyConfiguration": {
        "useApifyProxy": False  # Test without proxy first
    },
    "diagnostics": True,
    "fingerprintInjection": True  # Enable full anti-fingerprinting
}

import json
os.makedirs('apify_storage/key_value_stores/default', exist_ok=True)
with open('apify_storage/key_value_stores/default/INPUT.json', 'w') as f:
    json.dump(test_input, f)

print("=" * 60)
print("TESTING APIFY ACTOR LOCALLY")
print("=" * 60)
print(f"Test config: {json.dumps(test_input, indent=2)}")
print("=" * 60)

# Import and run the actual actor
sys.path.insert(0, 'src')
from main import main

asyncio.run(main())
