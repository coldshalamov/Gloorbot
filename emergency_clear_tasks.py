"""
Emergency script to clear all tasks and re-seed with Florida stores.
This bypasses the admin dashboard and directly manipulates the database.
"""
import requests
import json

COORDINATOR_URL = "https://gloorbot-coordinator.onrender.com"

print("=" * 60)
print("EMERGENCY TASK RESET")
print("=" * 60)
print()

# Step 1: Check current status
print("Step 1: Checking current task status...")
try:
    response = requests.get(f"{COORDINATOR_URL}/api/v1/status", timeout=10)
    if response.ok:
        status = response.json()
        tasks = status.get("tasks", {})
        print(f"  Total tasks: {tasks.get('total', 0)}")
        print(f"  Completed: {tasks.get('completed', 0)}")
        print(f"  In progress: {tasks.get('in_progress', 0)}")
    else:
        print(f"  ❌ Failed to get status: {response.status_code}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print()
print("=" * 60)
print("IMPORTANT: This script cannot directly clear tasks.")
print("You need to use the admin dashboard or SSH into Render.")
print("=" * 60)
print()
print("Option 1: Fix the admin dashboard (RECOMMENDED)")
print("  1. Push the store_config.py fix to GitHub")
print("  2. Wait for Render to redeploy (~2 minutes)")
print("  3. Use the admin dashboard to save Florida config")
print()
print("Option 2: Manual database access (ADVANCED)")
print("  1. Go to Render dashboard")
print("  2. Click on 'gloorbot-coordinator' service")
print("  3. Click 'Shell' tab")
print("  4. Run: python -c 'from coordinator_app.db import db_session; from coordinator_app.models import Task; from sqlalchemy import delete; db = db_session(); db.execute(delete(Task)); db.commit(); print(\"Tasks cleared\")'")
print()
print("After clearing tasks, the admin dashboard will re-seed them")
print("with the Florida configuration you selected.")
print()
