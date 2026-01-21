"""
EMERGENCY: Direct API call to set Florida configuration.
This bypasses any potential issues with the admin UI.
"""
import requests
import json
import sys

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

# The 18 Stuart-to-Miami stores
STUART_MIAMI_STORES = [
    '1109',  # Stuart
    '1962',  # West Palm Beach
    '1720',  # Lake Park
    '0654',  # Royal Palm Beach
    '1111',  # Boynton Beach
    '1069',  # Boca Raton
    '1792',  # Pompano Beach
    '0704',  # Coral Springs
    '0754',  # Oakland Park
    '1113',  # Fort Lauderdale? (check ID)
    '1681',  # Pembroke Pines
    '0725',  # Southwest Ranches
    '3315',  # Davie
    '2254',  # Hialeah
    '1841',  # Hialeah (N.W. Miami-Dade)
    '2707',  # Homestead
    '2904',  # Miami (Kendall)
    '3413',  # North Miami Beach
]

print("=" * 70)
print("EMERGENCY FLORIDA CONFIG SETTER")
print("=" * 70)
print()
print(f"This will configure workers to ONLY scrape these {len(STUART_MIAMI_STORES)} Florida stores:")
print()
for store_id in STUART_MIAMI_STORES[:5]:
    print(f"  - Store #{store_id}")
print(f"  ... and {len(STUART_MIAMI_STORES) - 5} more")
print()

# We need admin auth token to use the admin API
# Let's prompt for credentials
print("To set Florida config, you need to be logged into the admin dashboard.")
print()
print("OPTION 1: Manual API Test")
print("-" * 40)
print("1. Open browser to:", f"{COORDINATOR_URL}/admin/dashboard")
print("2. Open browser DevTools (F12)")
print("3. Go to Application tab -> Local Storage")
print("4. Copy the 'admin_token' value")
print()

token = input("Paste admin_token here (or press Enter to skip): ").strip()

if not token:
    print()
    print("No token provided. Can't make admin API call.")
    print()
    print("OPTION 2: Check if save works via UI")
    print("-" * 40)
    print("1. Go to admin dashboard")
    print("2. Click Southeast (FL) tab")
    print("3. Click '🌴 Stuart to Miami (18)' button")
    print("4. Click 'Save Configuration'")
    print("5. Look at the toast message - does it show success or error?")
    print("6. Check Render logs for any errors")
    sys.exit(0)

print()
print("Attempting to save Florida config...")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "enabled_states": ["FL"],
    "enabled_stores": STUART_MIAMI_STORES
}

try:
    response = requests.post(
        f"{COORDINATOR_URL}/admin/api/config",
        json=payload,
        headers=headers,
        timeout=60
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text[:500]}")
    
    if response.ok:
        data = response.json()
        print()
        print("✅ SUCCESS!")
        print(f"   Tasks cleared: {data.get('tasks_cleared', 'unknown')}")
        print(f"   Tasks inserted: {data.get('tasks_inserted', 'unknown')}")
        print()
        print("Workers should now switch to Florida on their next task request!")
        print("Click 'Kill' then 'Join' in the worker GUI to speed this up.")
    else:
        print()
        print("❌ FAILED!")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
