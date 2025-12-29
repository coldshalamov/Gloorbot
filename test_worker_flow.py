"""
Test script that mimics a worker submitting deals to coordinator,
which should then forward to CheapSkater.
"""

import requests
from datetime import datetime
import time

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

# Create a test deal in EXACT format that worker uses
test_deal = {
    "store_id": "1089",
    "store_name": "Auburn, WA (#1089)",
    "category_url": "https://www.lowes.com/pl/Paint-supplies/4294937309",
    "product_url": f"https://www.lowes.com/pd/TEST-Worker-Flow/{int(time.time())}",
    "title": f"TEST Worker Flow - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "price": 12.99,
    "was_price": 59.99,
    "pct_off": 0.7834,
    "found_at": datetime.utcnow().isoformat()
}

print("=" * 70)
print("TESTING WORKER -> COORDINATOR -> CHEAPSKATER FLOW")
print("=" * 70)

print("\nTest Deal:")
print(f"  Title: {test_deal['title']}")
print(f"  Price: ${test_deal['price']} (was ${test_deal['was_price']})")
print(f"  Discount: {test_deal['pct_off']*100:.1f}% off")
print(f"  Store: {test_deal['store_name']}")

print("\n" + "=" * 70)
print("STEP 1: Submit deal to Coordinator (mimicking worker)")
print("=" * 70)

payload = {
    "client_id": "test_worker_flow",
    "deals": [test_deal]
}

try:
    resp = requests.post(
        f"{COORDINATOR_URL}/api/v1/deals/bulk",
        json=payload,
        timeout=30
    )
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")

    if resp.status_code == 200:
        print("\n[OK] Deal submitted to coordinator successfully!")
    else:
        print(f"\n[FAIL] Coordinator returned error: {resp.status_code}")
        exit(1)
except Exception as e:
    print(f"\n[FAIL] Error submitting to coordinator: {e}")
    exit(1)

print("\n" + "=" * 70)
print("STEP 2: Wait for coordinator to forward to CheapSkater")
print("=" * 70)
print("Waiting 3 seconds for forwarding...")
time.sleep(3)

print("\n" + "=" * 70)
print("STEP 3: Check if deal appears on CheapSkater")
print("=" * 70)
print("\nTo verify the deal made it through:")
print("1. Visit: https://cheapskater.onrender.com")
print("2. Look for deal with title starting with 'TEST Worker Flow'")
print("3. Should show $12.99 (was $59.99) - 78% off")
print("\nIf you see it, the integration is working end-to-end!")

print("\n" + "=" * 70)
print("BONUS: Check Gloorbot coordinator recent deals")
print("=" * 70)

try:
    resp = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nRecent deals in coordinator (last {len(data['recent_deals'])}):")
        for deal in data['recent_deals'][:5]:
            print(f"  - {deal['title'][:60]}")
            print(f"    ${deal['price']} (was ${deal['was_price']}) - {deal['pct_off']*100:.0f}% off")
            print(f"    Store: {deal['store_name']}")
except Exception as e:
    print(f"Could not fetch coordinator status: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
