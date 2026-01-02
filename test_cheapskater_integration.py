"""
Test CheapSkater Integration - Verify data is being sent correctly

This script tests the CheapSkater integration by:
1. Creating a test product
2. Sending it to CheapSkater
3. Verifying it appears on the website

Usage:
    python test_cheapskater_integration.py
    python test_cheapskater_integration.py --url https://your-cheapskater.com
"""

import os
import sys
import time
import uuid
import requests
from datetime import datetime, timezone

# Configuration
CHEAPSKATER_URL = os.getenv("CHEAPSKATER_URL", "https://cheapskater.onrender.com")
CHEAPSKATER_API_KEY = os.getenv("CHEAPSKATER_API_KEY", "")

# Generate unique test marker
TEST_ID = str(uuid.uuid4())[:8]
TEST_SKU = f"TEST{int(time.time())}"
TEST_TITLE = f"GLOORBOT_INTEGRATION_TEST_{TEST_ID}"

def test_integration():
    """Test the complete integration flow."""
    print("🧪 Testing CheapSkater Integration")
    print(f"📍 CheapSkater URL: {CHEAPSKATER_URL}")
    print(f"🔑 Test Marker: {TEST_TITLE}")
    print()
    
    # Step 1: Create test deal
    print("[1/3] Creating test deal...")
    test_deal = {
        "store_id": "0004",
        "store_name": "Lowe's Rainier, Seattle, WA",
        "category_url": "https://www.lowes.com/pl/Clearance/0",
        "product_url": f"https://www.lowes.com/pd/Test-Product/{TEST_SKU}",
        "title": TEST_TITLE,
        "price": 9.99,
        "was_price": 99.99,
        "pct_off": 0.90,
        "found_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  ✅ Created: {test_deal['title']}")
    print()
    
    # Step 2: Send to CheapSkater
    print("[2/3] Sending to CheapSkater ingest API...")
    try:
        headers = {}
        if CHEAPSKATER_API_KEY:
            headers["X-API-Key"] = CHEAPSKATER_API_KEY
            print(f"  🔐 Using API key: {CHEAPSKATER_API_KEY[:8]}...")
        
        response = requests.post(
            f"{CHEAPSKATER_URL}/api/ingest/deals",
            json={"source": "gloorbot-test", "deals": [test_deal]},
            headers=headers,
            timeout=30
        )
        
        print(f"  📡 Response status: {response.status_code}")
        
        if response.status_code == 404:
            print()
            print("❌ FAILED: Ingest API not found (404)")
            print()
            print("The CheapSkater ingest API is not installed. You need to:")
            print("1. Copy integration/ingest.py to your CheapSkater repo as app/ingest.py")
            print("2. Add to app/dashboard.py:")
            print("   from app.ingest import router as ingest_router")
            print("   app.include_router(ingest_router)")
            print("3. Redeploy CheapSkater")
            return False
        
        response.raise_for_status()
        result = response.json()
        
        print(f"  ✅ Accepted: {result.get('accepted', 0)}")
        print(f"  ⚠️  Errors: {result.get('errors', 0)}")
        print(f"  💬 Message: {result.get('message', 'N/A')}")
        print()
        
        if result.get('accepted', 0) == 0:
            print("❌ FAILED: Deal was not accepted")
            return False
            
    except requests.exceptions.ConnectionError:
        print()
        print(f"❌ FAILED: Cannot connect to {CHEAPSKATER_URL}")
        print("   Is the CheapSkater website running?")
        return False
    except requests.exceptions.Timeout:
        print()
        print("❌ FAILED: Request timed out")
        return False
    except requests.exceptions.HTTPError as e:
        print()
        print(f"❌ FAILED: HTTP error {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return False
    except Exception as e:
        print()
        print(f"❌ FAILED: {e}")
        return False
    
    # Step 3: Verify on website
    print("[3/3] Verifying on CheapSkater website...")
    print("  ⏳ Waiting 3 seconds for propagation...")
    time.sleep(3)
    
    try:
        # Try to fetch recent clearance deals
        check_response = requests.get(
            f"{CHEAPSKATER_URL}/api/clearance?scope=all&sort_order=newest&limit=50",
            timeout=30
        )
        check_response.raise_for_status()
        data = check_response.json()
        
        # Look for our test deal
        found = False
        for item in data.get("items", []):
            if TEST_TITLE in item.get("title", ""):
                found = True
                print()
                print("🎉 SUCCESS! Test deal found on CheapSkater!")
                print(f"   Title: {item.get('title')}")
                print(f"   Price: ${item.get('price')} (was ${item.get('price_was')})")
                print(f"   Store: {item.get('store_name')}")
                print()
                print("✅ Integration is working correctly!")
                print()
                print(f"🌐 View it at: {CHEAPSKATER_URL}")
                return True
        
        if not found:
            print()
            print("⚠️  WARNING: Deal was accepted but not found in recent items")
            print("   Possible reasons:")
            print("   - Data takes longer than 3s to appear")
            print("   - Deal was filtered out by CheapSkater logic")
            print("   - API endpoint returns different data than expected")
            print()
            print(f"   Check manually at: {CHEAPSKATER_URL}")
            return None  # Uncertain
            
    except Exception as e:
        print()
        print(f"⚠️  Could not verify on website: {e}")
        print(f"   Check manually at: {CHEAPSKATER_URL}")
        return None  # Uncertain
    
    return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CheapSkater integration")
    parser.add_argument("--url", help="CheapSkater URL", default=CHEAPSKATER_URL)
    parser.add_argument("--api-key", help="API key", default=CHEAPSKATER_API_KEY)
    args = parser.parse_args()
    
    CHEAPSKATER_URL = args.url
    CHEAPSKATER_API_KEY = args.api_key
    
    result = test_integration()
    
    if result is True:
        sys.exit(0)  # Success
    elif result is False:
        sys.exit(1)  # Failure
    else:
        sys.exit(2)  # Uncertain
