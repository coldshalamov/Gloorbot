"""
Test script to directly call the coordinator admin API and see what happens.
"""
import requests
import json

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

# First, let's see what the current config looks like
print("=" * 70)
print("TESTING ADMIN API")
print("=" * 70)
print()

# We need to be logged in to test admin endpoints
# Let's just check the status first to see what tasks exist

print("Step 1: Checking current status...")
try:
    response = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
    if response.ok:
        status = response.json()
        print(f"  Tasks total: {status.get('tasks', {}).get('total', 0)}")
        print(f"  Tasks completed: {status.get('tasks', {}).get('completed', 0)}")
        print(f"  Deals total: {status.get('deals', {}).get('total', 0)}")
        print()
        
        # Check if there's any hint about which states are being scraped
        print("Full status response:")
        print(json.dumps(status, indent=2))
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 70)
print()
print("The issue is that the admin save needs to:")
print("1. Clear all existing tasks (DELETE FROM tasks)")
print("2. Write a new urls.txt with Florida stores")
print("3. Re-seed tasks from that new urls.txt")
print()
print("If task count is still 10,976, the save never succeeded.")
print()
