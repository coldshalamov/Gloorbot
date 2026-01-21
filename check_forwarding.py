"""
Check if Gloorbot is configured to forward deals to Cheapskater.
"""
import requests

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

print("=" * 70)
print("GLOORBOT → CHEAPSKATER FORWARDING DIAGNOSTIC")
print("=" * 70)
print()

# Check coordinator status
print("Step 1: Checking Gloorbot Coordinator...")
try:
    response = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
    if response.ok:
        status = response.json()
        print(f"  ✅ Coordinator is online")
        
        deals = status.get("deals", {})
        total = deals.get("total", 0)
        today = deals.get("today", 0)
        
        print(f"  💰 Total deals in Gloorbot DB: {total:,}")
        print(f"  📅 Deals today: {today:,}")
        
        if total == 0:
            print()
            print("  ⚠️  PROBLEM: Gloorbot has 0 deals in its database!")
            print("     This means:")
            print("     - Workers aren't finding any 50%+ deals, OR")
            print("     - Workers aren't submitting deals to coordinator, OR")
            print("     - Deal submission is failing")
            print()
    else:
        print(f"  ❌ Failed: HTTP {response.status_code}")
        exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

print()
print("Step 2: Checking Cheapskater website...")
CHEAPSKATER_URL = "https://cheapskater.onrender.com"
try:
    response = requests.get(f"{CHEAPSKATER_URL}/api/deals?limit=1", timeout=10)
    if response.ok:
        deals = response.json()
        if isinstance(deals, list):
            count = len(deals)
        else:
            count = deals.get("total", 0)
        
        print(f"  ✅ Cheapskater is online")
        print(f"  📦 Deals in Cheapskater DB: {count if count > 0 else 'Unknown (check manually)'}")
    else:
        print(f"  ❌ Failed: HTTP {response.status_code}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()
print("=" * 70)
print("DIAGNOSIS")
print("=" * 70)
print()

if total == 0:
    print("🔴 CRITICAL: Gloorbot has 0 deals")
    print()
    print("Possible causes:")
    print("1. Workers aren't finding any 50%+ deals (check worker logs)")
    print("2. Workers are blocked/erroring (check Render logs)")
    print("3. Deal submission is broken (check coordinator logs)")
    print()
    print("Next steps:")
    print("- Check Render logs for gloorbot-coordinator")
    print("- Look for lines like:")
    print("  [DEALS] batch_id=... upserted=0  ← No deals being saved")
    print("  [FORWARD] batch_id=... count=X   ← Forwarding attempts")
    print()
else:
    print(f"✅ Gloorbot has {total} deals")
    print()
    print("If Cheapskater shows 0 deals but Gloorbot has deals:")
    print("- Forwarding is broken")
    print("- Check CHEAPSKATER_INGEST_URL env var on Render")
    print("- Check CHEAPSKATER_INGEST_API_KEY env var on Render")
    print()
    print("Expected env vars on Render:")
    print("  CHEAPSKATER_INGEST_URL=https://cheapskater.onrender.com/api/ingest")
    print("  CHEAPSKATER_INGEST_API_KEY=rescue-key-2026")
