import requests
import json
import time
import uuid

# Configuration
COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"
CHEAPSKATER_URL = "https://cheapskater.onrender.com"

# Generate a unique "marker" title so we can find it
UNIQUE_ID = str(uuid.uuid4())[:8]
TEST_SKU = "999999999"
TEST_TITLE = f"GLOORBOT_END_TO_END_TEST_{UNIQUE_ID}"
TEST_STORE = "0000" # Dummy store

def test_pipeline():
    print(f"🔍 Starting End-to-End Pipeline Verification")
    print(f"📍 Coordinator: {COORDINATOR_URL}")
    print(f"📍 CheapSkater: {CHEAPSKATER_URL}")
    print(f"🔑 Marker Title: {TEST_TITLE}")
    
    # 1. Register as a fake worker
    print("\n[1] Registering dummy worker...")
    try:
        reg_res = requests.post(f"{COORDINATOR_URL}/api/v1/client/register", 
                               json={"hostname": "test-script", "version": "0.0.0"}, timeout=10)
        reg_res.raise_for_status()
        client_id = reg_res.json()["client_id"]
        print(f"    ✅ Registered (Client ID: {client_id})")
    except Exception as e:
        print(f"    ❌ Registration failed: {e}")
        return

    # 2. Submit a fake deal
    print("\n[2] Submitting test deal to Coordinator...")
    test_deal = {
        "store_id": TEST_STORE,
        "store_name": "Test Store",
        "category_url": "https://www.lowes.com/c/Test",
        "product_url": f"https://www.lowes.com/pd/Test-Product/{TEST_SKU}",
        "title": TEST_TITLE,
        "price": 10.00,
        "was_price": 100.00,
        "pct_off": 0.90
    }
    
    try:
        submit_res = requests.post(f"{COORDINATOR_URL}/api/v1/deals/bulk",
                                  json={"client_id": client_id, "deals": [test_deal]}, timeout=10)
        submit_res.raise_for_status()
        print(f"    ✅ Deal Submitted (Response: {submit_res.json()})")
    except Exception as e:
        print(f"    ❌ Submission failed: {e}")
        return

    # 3. Check CheapSkater
    print("\n[3] Waiting 5s for propagation...")
    time.sleep(5)
    
    print("\n[4] Checking CheapSkater API for the deal...")
    try:
        # Search for our unique sku or check new arrivals
        # Cheapskater has /api/clearance, likely sorts by newest by default
        check_res = requests.get(f"{CHEAPSKATER_URL}/api/clearance?scope=all&sort_order=newest", timeout=30)
        check_res.raise_for_status()
        data = check_res.json()
        
        found = False
        for item in data.get("items", []):
            if item.get("title") == TEST_TITLE:
                found = True
                print(f"\n🎉 SUCCESS! Found the test deal on CheapSkater!")
                print(f"   Item: {item['title']}")
                print(f"   Price: ${item['price']} (Was ${item['price_was']})")
                break
        
        if not found:
            print(f"\n❌ FAILURE: Deal was submitted but NOT found on CheapSkater.")
            print("   Possible causes:")
            print("   1. Coordinator does not have 'CHEAPSKATER_INGEST_URL' env var set.")
            print("   2. CheapSkater rejected the ingest request.")
            print("   3. Propagation is slower than 5s.")
            
    except Exception as e:
        print(f"    ❌ Check failed: {e}")

if __name__ == "__main__":
    test_pipeline()
