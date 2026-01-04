#[INFO]/usr/bin/env python3
"""
Test the full Gloorbot → CheapSkater data flow.
Sends test deals and verifies they reach both systems.
"""

import requests
import sqlite3
import time
from datetime import datetime
from pathlib import Path

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"
CHEAPSKATER_URL = "https://cheapskater.onrender.com"
CHEAPSKATER_API_KEY = "JZhdARITo9ujVU2OcCaiqkx6ktB7SNh28ouQXz6U2f0="

def test_coordinator_health():
    """Test if coordinator is reachable."""
    print("\n[1/5] Testing Coordinator Health...")
    try:
        resp = requests.get(f"{COORDINATOR_URL}/healthz", timeout=5)
        if resp.status_code == 200:
            print("  [OK] Coordinator is healthy")
            return True
        else:
            print(f"  [ERROR] Coordinator returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [ERROR] Cannot reach coordinator: {e}")
        return False

def test_cheapskater_health():
    """Test if CheapSkater ingest endpoint is ready."""
    print("\n[2/5] Testing CheapSkater Ingest Health...")
    try:
        resp = requests.get(f"{CHEAPSKATER_URL}/api/ingest/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  [OK] CheapSkater ingest endpoint is ready")
            print(f"    Configured: {data.get('configured')}")
            return True
        else:
            print(f"  [ERROR] CheapSkater returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [ERROR] Cannot reach CheapSkater: {e}")
        return False

def send_test_deal():
    """Send a test deal to CheapSkater ingest endpoint."""
    print("\n[3/5] Sending Test Deal to CheapSkater...")

    test_deal = {
        "source": "gloorbot_integration_test",
        "deals": [
            {
                "store_id": "INTEG-TEST",
                "store_name": "Integration Test Store, WA",
                "category_url": "https://www.lowes.com/pl/Test-Category/123456789",
                "product_url": "https://www.lowes.com/pd/Integration-Test-Product/8888888",
                "title": "INTEGRATION TEST PRODUCT - DO NOT BUY",
                "price": 29.99,
                "was_price": 99.99,
                "pct_off": 0.70,
                "found_at": datetime.utcnow().isoformat() + "Z",
            }
        ]
    }

    headers = {
        "X-API-Key": CHEAPSKATER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            f"{CHEAPSKATER_URL}/api/ingest/deals",
            json=test_deal,
            headers=headers,
            timeout=10
        )

        if resp.status_code == 200:
            result = resp.json()
            print(f"  [OK] Test deal accepted")
            print(f"    Accepted: {result.get('accepted')}")
            print(f"    Errors: {result.get('errors')}")
            return result.get('accepted', 0) > 0
        else:
            print(f"  [ERROR] Ingest failed: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [ERROR] Failed to send test deal: {e}")
        return False

def check_local_database():
    """Check if deals are in the local CheapSkater database copy."""
    print("\n[4/5] Checking Local CheapSkater Database...")

    db_path = Path("C:/Users/User/Documents/GitHub/Telomere/CheapSkater-/orwa_lowes.sqlite")

    if not db_path.exists():
        print(f"  [INFO] Local database not found at {db_path}")
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check test deal
        cursor.execute("SELECT COUNT(*) FROM store_price_history WHERE sku = '8888888'")
        count = cursor.fetchone()[0]

        conn.close()

        if count > 0:
            print(f"  [OK] Test deal found in local database[INFO]")
            print(f"    Records: {count}")
            return True
        else:
            cursor.execute("SELECT COUNT(*) FROM store_price_history")
            total = cursor.fetchone()[0]
            print(f"  [ERROR] Test deal NOT in database")
            print(f"    Total records in store_price_history: {total}")

            # Check if there are ANY recent records
            if total > 0:
                cursor.execute("""
                    SELECT sku, title FROM store_price_history
                    ORDER BY updated_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    print(f"    Most recent: SKU={row[0]}, Title={row[1][:50]}")

            return False
    except Exception as e:
        print(f"  [INFO] Error checking database: {e}")
        return None

def check_coordinator_status():
    """Check coordinator status for total deals."""
    print("\n[5/5] Checking Coordinator Deal Count...")

    try:
        resp = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            total_deals = len(data.get('recent_deals', []))

            print(f"  [OK] Coordinator status retrieved")
            print(f"    Total tasks: {data['tasks']['total']}")
            print(f"    Completed: {data['tasks']['completed']}")
            print(f"    Recent deals: {total_deals}")

            if total_deals > 0:
                first_deal = data['recent_deals'][0]
                print(f"    Most recent: {first_deal['title'][:50]}")
                print(f"    Last seen: {first_deal['last_seen_at']}")

            return True
        else:
            print(f"  [ERROR] Cannot get coordinator status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [ERROR] Error checking coordinator: {e}")
        return False

def main():
    print("="*70)
    print("GLOORBOT -> CHEAPSKATER INTEGRATION TEST")
    print("="*70)
    print(f"Time: {datetime.now().isoformat()}")

    # Run tests
    coord_ok = test_coordinator_health()
    cheap_ok = test_cheapskater_health()

    if not (coord_ok and cheap_ok):
        print("\n[ERROR] Services are not healthy. Cannot continue.")
        return

    deal_ok = send_test_deal()

    if deal_ok:
        print("\n[INFO] Giving database 5 seconds to process...")
        time.sleep(5)

    db_ok = check_local_database()
    status_ok = check_coordinator_status()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if db_ok is True:
        print("[OK] END-TO-END SUCCESS: Data is flowing from Gloorbot -> CheapSkater")
        print("  Your scraper data should be visible on the CheapSkater dashboard")
    elif db_ok is False:
        print("[ERROR] DATA NOT REACHING CHEAPSKATER: Test deal was rejected by ingest")
        print("  Check CheapSkater logs on Render for error messages")
        print("  The error logging should now show what's failing")
    else:
        print("? UNCERTAIN: Could not verify database status")
        print("  Check the CheapSkater service on Render for any errors")

    print("\nNext steps:")
    print("1. Check Render logs for CheapSkater (should show error details)")
    print("2. If ingest is working, run your actual scraper")
    print("3. Monitor https://cheapskater.onrender.com/ for deals appearing")

if __name__ == "__main__":
    main()
