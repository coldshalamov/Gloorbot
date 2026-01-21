"""
Check if deals are being sent to Cheapskater and if they have images.
"""
import requests
from datetime import datetime, timedelta

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

print("=" * 70)
print("GLOORBOT → CHEAPSKATER DIAGNOSTIC")
print("=" * 70)
print()

# Step 1: Check coordinator status
print("Step 1: Checking Gloorbot Coordinator status...")
try:
    response = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
    if response.ok:
        status = response.json()
        print(f"  ✅ Coordinator is online")
        
        tasks = status.get("tasks", {})
        print(f"  📦 Total tasks: {tasks.get('total', 0):,}")
        print(f"  ✅ Completed: {tasks.get('completed', 0):,}")
        print(f"  🔄 In progress: {tasks.get('in_progress', 0):,}")
        
        clients = status.get("clients", {})
        print(f"  👥 Active workers: {clients.get('active', 0)}")
        
        deals = status.get("deals", {})
        print(f"  💰 Total deals found: {deals.get('total', 0):,}")
        print(f"  📅 Deals today: {deals.get('today', 0):,}")
    else:
        print(f"  ❌ Failed: HTTP {response.status_code}")
        exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    exit(1)

print()

# Step 2: Check recent deals from coordinator
print("Step 2: Checking recent deals in Gloorbot database...")
try:
    # The coordinator doesn't have a public endpoint to list deals
    # But we can check the debug endpoint if available
    response = requests.get(f"{COORDINATOR_URL}/api/v1/debug/recent-deals", timeout=10)
    if response.ok:
        recent = response.json()
        print(f"  Found {len(recent)} recent deals")
        if recent:
            for deal in recent[:3]:
                has_image = bool(deal.get("image_url"))
                print(f"    {'✅' if has_image else '❌'} {deal.get('title', 'Unknown')[:50]}...")
                if not has_image:
                    print(f"       ⚠️  Missing image_url!")
    else:
        print(f"  ℹ️  Debug endpoint not available (expected)")
except Exception:
    print(f"  ℹ️  Debug endpoint not available (expected)")

print()

# Step 3: Check Cheapskater
print("Step 3: Checking Cheapskater website...")
CHEAPSKATER_URL = "https://cheapskater.onrender.com"
try:
    response = requests.get(f"{CHEAPSKATER_URL}/api/deals?limit=10", timeout=10)
    if response.ok:
        deals = response.json()
        total = len(deals) if isinstance(deals, list) else deals.get("total", 0)
        print(f"  ✅ Cheapskater is online")
        print(f"  📦 Recent deals: {total}")
        
        if isinstance(deals, list) and deals:
            print()
            print("  Last 3 deals:")
            for deal in deals[:3]:
                has_image = bool(deal.get("image_url"))
                found_at = deal.get("found_at", "")
                print(f"    {'✅' if has_image else '❌'} {deal.get('title', 'Unknown')[:50]}...")
                print(f"       Found: {found_at}")
                if not has_image:
                    print(f"       ⚠️  Missing image!")
    else:
        print(f"  ❌ Failed: HTTP {response.status_code}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()
print("=" * 70)
print("DIAGNOSIS")
print("=" * 70)

print("""
If you see:
  ❌ Missing image on multiple deals → Image extraction is broken
  ✅ Deals in Gloorbot but not Cheapskater → Forwarding is broken
  📦 0 deals today → Workers aren't finding any deals (check threshold)
  🔄 0 tasks in progress → Workers aren't connected
""")
