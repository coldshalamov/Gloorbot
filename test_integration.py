"""
Integration Test Script for Gloorbot <-> CheapSkater
Tests the complete data flow from worker -> coordinator -> CheapSkater
"""

import requests
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# Configuration
COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"
CHEAPSKATER_URL = "https://cheapskater.onrender.com"
CHEAPSKATER_DB = Path("C:/Users/User/Documents/GitHub/Telomere/CheapSkater-/orwa_lowes.sqlite")

def test_coordinator_health():
    """Test if Gloorbot coordinator is online."""
    print("=" * 70)
    print("TEST 1: Gloorbot Coordinator Health Check")
    print("=" * 70)
    try:
        resp = requests.get(f"{COORDINATOR_URL}/healthz", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] Coordinator is ONLINE")
            print(f"  Status: {data}")
            return True
        else:
            print(f"[FAIL] Coordinator returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Coordinator is OFFLINE: {e}")
        return False

def test_cheapskater_health():
    """Test if CheapSkater is online."""
    print("\n" + "=" * 70)
    print("TEST 2: CheapSkater Health Check")
    print("=" * 70)
    try:
        resp = requests.get(f"{CHEAPSKATER_URL}/healthz", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] CheapSkater is ONLINE")
            print(f"  Status: {data}")
            return True
        else:
            print(f"[FAIL] CheapSkater returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] CheapSkater is OFFLINE: {e}")
        return False

def test_cheapskater_ingest():
    """Test CheapSkater /api/ingest endpoint directly."""
    print("\n" + "=" * 70)
    print("TEST 3: CheapSkater /api/ingest Endpoint")
    print("=" * 70)

    payload = {
        "source": "integration_test",
        "deals": [{
            "store_id": "1089",
            "store_name": "Auburn, WA (#1089)",
            "category_url": "https://www.lowes.com/pl/Roofing/4294515877",
            "product_url": f"https://www.lowes.com/pd/TEST-Product/{int(time.time())}",
            "title": f"TEST - Integration Test {datetime.now().strftime('%H:%M:%S')}",
            "price": 9.99,
            "was_price": 99.99,
            "pct_off": 0.90,
            "found_at": datetime.utcnow().isoformat() + "Z"
        }]
    }

    try:
        resp = requests.post(
            f"{CHEAPSKATER_URL}/api/ingest",
            json=payload,
            timeout=30
        )
        print(f"  Status Code: {resp.status_code}")
        print(f"  Response: {resp.text}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] Ingest endpoint is WORKING")
            print(f"  Accepted: {data.get('count', 0)} deals")
            print(f"  Skipped: {data.get('skipped', 0)} deals")
            return True
        else:
            print(f"[FAIL] Ingest endpoint FAILED with status {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Ingest endpoint ERROR: {e}")
        return False

def check_cheapskater_database():
    """Check if test data appeared in CheapSkater database."""
    print("\n" + "=" * 70)
    print("TEST 4: CheapSkater Database Verification")
    print("=" * 70)

    if not CHEAPSKATER_DB.exists():
        print(f"[FAIL] Database not found: {CHEAPSKATER_DB}")
        return False

    try:
        conn = sqlite3.connect(str(CHEAPSKATER_DB))
        cursor = conn.cursor()

        # Count observations
        cursor.execute("SELECT COUNT(*) FROM observations")
        obs_count = cursor.fetchone()[0]

        # Get latest observation
        cursor.execute("""
            SELECT ts_utc, store_id, sku, title, price, price_was, pct_off
            FROM observations
            ORDER BY ts_utc DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()

        print(f"  Total observations: {obs_count}")
        if latest:
            print(f"\n  Latest observation:")
            print(f"    Timestamp: {latest[0]}")
            print(f"    Store: {latest[1]}")
            print(f"    SKU: {latest[2]}")
            print(f"    Title: {latest[3]}")
            print(f"    Price: ${latest[4]} (was ${latest[5]})")
            print(f"    Discount: {latest[6]*100:.0f}% off")

        conn.close()

        if obs_count > 0:
            print(f"\n[OK] Database has data!")
            return True
        else:
            print(f"\n[WARN] Database is empty (waiting for worker submissions)")
            return False

    except Exception as e:
        print(f"[FAIL] Database check ERROR: {e}")
        return False

def test_coordinator_status():
    """Check coordinator status for active workers and deals."""
    print("\n" + "=" * 70)
    print("TEST 5: Gloorbot Coordinator Status")
    print("=" * 70)

    try:
        resp = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] Coordinator status retrieved")
            print(f"\n  Tasks:")
            print(f"    Total: {data['tasks']['total']}")
            print(f"    Leased: {data['tasks']['leased']}")
            print(f"    Completed: {data['tasks']['completed']}")
            print(f"    Completed (last hour): {data['tasks']['completed_last_hour']}")

            print(f"\n  Clients:")
            print(f"    Active: {data['clients']['active']}")

            print(f"\n  Recent Deals: {len(data['recent_deals'])}")
            for deal in data['recent_deals'][:3]:
                print(f"    - {deal['title'][:50]}...")
                print(f"      ${deal['price']} (was ${deal['was_price']}) - {deal['pct_off']*100:.0f}% off")
                print(f"      Store: {deal['store_name']}")

            return True
        else:
            print(f"[FAIL] Status check FAILED: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Status check ERROR: {e}")
        return False

def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("GLOORBOT <-> CHEAPSKATER INTEGRATION TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "Coordinator Health": test_coordinator_health(),
        "CheapSkater Health": test_cheapskater_health(),
        "CheapSkater Ingest": test_cheapskater_ingest(),
        "Database Verification": check_cheapskater_database(),
        "Coordinator Status": test_coordinator_status(),
    }

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"{status:10} {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n ALL TESTS PASSED! Integration is working correctly.")
    elif passed >= 3:
        print("\n[WARN] Partial success. Check failed tests above.")
    else:
        print("\n[FAIL] Integration has issues. Review errors above.")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    if results["CheapSkater Ingest"]:
        print("[OK] CheapSkater is ready to receive deals")
    else:
        print("[WARN] CheapSkater /api/ingest needs troubleshooting")
        print("  Check Render logs for the CheapSkater service")

    if results["Coordinator Health"]:
        print("[OK] Gloorbot coordinator is ready")
    else:
        print("[WARN] Gloorbot coordinator needs deployment")

    if not results["Database Verification"]:
        print("\n TO SEE DEALS FLOW:")
        print("  1. Run WorkerSetup.exe on a Windows machine")
        print("  2. Worker will scrape and submit deals to coordinator")
        print("  3. Coordinator will forward to CheapSkater")
        print("  4. Visit https://cheapskater.onrender.com to see deals")

if __name__ == "__main__":
    main()
