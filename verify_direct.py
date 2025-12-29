import requests
import json
import uuid

CHEAPSKATER_URL = "https://cheapskater.onrender.com"
UNIQUE_ID = str(uuid.uuid4())[:8]
TEST_TITLE = f"DIRECT_INGEST_TEST_{UNIQUE_ID}"

def test_direct():
    print(f"Testing direct ingest to {CHEAPSKATER_URL}...")
    
    deal = {
        "store_id": "2638",
        "store_name": "Lowe's of Issaquah",
        "category_url": "https://lowes.com",
        "product_url": "https://www.lowes.com/pd/Test/5013600965",
        "title": TEST_TITLE,
        "price": 5.00,
        "was_price": 50.00,
        "pct_off": 0.90,
        "found_at": "2023-10-27T10:00:00Z" # Dummy date
    }
    
    payload = {
        "source": "verify_script",
        "deals": [deal]
    }
    
    try:
        res = requests.post(f"{CHEAPSKATER_URL}/api/ingest", json=payload, timeout=30)
        res.raise_for_status()
        print(f"✅ Ingest POST successful: {res.json()}")
        
        # Now verify presence
        print("Checking for item...")
        res = requests.get(f"{CHEAPSKATER_URL}/api/clearance?scope=all&sort_order=newest", timeout=30)
        data = res.json()
        found = any(i.get("title") == TEST_TITLE for i in data.get("items", []))
        
        if found:
            print("🎉 SUCCESS: Item found in API list.")
        else:
            print("❌ FAILURE: Item ingested but not found in list.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_direct()
