"""
Show the latest worker logs to diagnose what's happening.
"""
import os
from pathlib import Path

# Find the logs directory
appdata = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
logs_dir = Path(appdata) / "GloorbotWorkerData" / "logs"

print("=" * 70)
print("WORKER LOG DIAGNOSTIC")
print("=" * 70)
print()
print(f"Looking for logs in: {logs_dir}")
print()

if not logs_dir.exists():
    print("❌ Logs directory doesn't exist!")
    print("   This means the worker hasn't run yet, or it's using a different path.")
    exit(1)

# Find all log files
log_files = list(logs_dir.glob("*.jsonl")) + list(logs_dir.glob("*.log"))
if not log_files:
    print("❌ No log files found!")
    print("   The worker might not be running or logging is disabled.")
    exit(1)

# Sort by modification time (newest first)
log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

print(f"✅ Found {len(log_files)} log files")
print()

# Show the most recent log file
latest = log_files[0]
print(f"📄 Latest log file: {latest.name}")
print(f"   Last modified: {latest.stat().st_mtime}")
print(f"   Size: {latest.stat().st_size:,} bytes")
print()

# Read last 50 lines
print("=" * 70)
print("LAST 50 LINES:")
print("=" * 70)
print()

try:
    with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        last_50 = lines[-50:] if len(lines) > 50 else lines
        for line in last_50:
            print(line.rstrip())
except Exception as e:
    print(f"❌ Error reading log: {e}")

print()
print("=" * 70)
print()
print("What to look for:")
print("  ✅ 'Category done: products_seen=X deals_sent=Y' → Working!")
print("  ❌ 'Access Denied' or 'blocked' → Getting blocked by Lowe's")
print("  ❌ 'Error' or 'Exception' → Something crashed")
print("  ⚠️  Nothing recent → Worker might not be running")
