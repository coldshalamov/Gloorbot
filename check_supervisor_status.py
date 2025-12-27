"""
Check Supervisor Status - Monitor from another terminal or Claude Code

Usage:
    python check_supervisor_status.py           # One-time check
    python check_supervisor_status.py --watch   # Continuous monitoring
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta

def format_duration(seconds):
    """Format seconds as human-readable duration"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"

def check_status():
    """Check and display supervisor status"""
    status_file = Path("scrape_output_supervised/supervisor_status.json")

    if not status_file.exists():
        print("❌ Supervisor not running (no status file found)")
        print("\nStart with: python intelligent_supervisor.py --state WA")
        return False

    # Check if file is recent (supervisor still alive)
    file_age = time.time() - status_file.stat().st_mtime
    if file_age > 120:  # 2 minutes old
        print(f"⚠️  WARNING: Status file is {file_age:.0f} seconds old")
        print("   Supervisor might have crashed!")
        print("")

    with open(status_file) as f:
        status = json.load(f)

    # Parse timestamp
    last_update = datetime.fromisoformat(status['timestamp'])
    now = datetime.now()
    update_ago = (now - last_update).total_seconds()

    print("="*70)
    print("SUPERVISOR STATUS")
    print("="*70)
    print(f"Last Update: {format_duration(update_ago)} ago")
    print(f"Uptime: {format_duration(status['uptime_seconds'])}")
    print("")

    # Stats
    stats = status['stats']
    print("📊 STATISTICS")
    print(f"  Total Products: {stats['total_products']:,}")
    print(f"  Workers Launched: {stats['workers_launched']}")
    print(f"  Current Workers: {stats['current_workers']}")
    print(f"  Failed/Restarted: {stats['workers_failed']}")
    print(f"  Blocking Incidents: {stats['blocking_incidents']}")
    print("")

    # Overall rate
    if status['uptime_seconds'] > 0:
        products_per_hour = (stats['total_products'] / status['uptime_seconds']) * 3600
        print(f"  Rate: {products_per_hour:.0f} products/hour")
        print("")

    # Workers
    workers = status['workers']
    if workers:
        print("👷 WORKERS")
        active = [w for w in workers if w['alive']]
        print(f"  Active: {len(active)}/{len(workers)}")
        print("")

        for w in workers:
            status_icon = "✅" if w['alive'] else "❌"
            print(f"  {status_icon} Worker {w['id']}: {w['store']}")
            print(f"     Products: {w['products']:,} ({w['products_per_min']:.1f}/min)")
            print(f"     Resources: {w['memory_mb']:.0f}MB RAM, {w['cpu_percent']:.1f}% CPU")

            if not w['alive']:
                print(f"     ⚠️  Not running")

            print("")

    else:
        print("⚠️  No workers yet")
        print("")

    # Health indicators
    print("🏥 HEALTH")
    all_workers = status['workers']
    if all_workers:
        active_workers = [w for w in all_workers if w['alive']]

        if not active_workers:
            print("  ❌ No active workers!")
        else:
            # Check for stalled workers
            stalled = [w for w in active_workers if w['products_per_min'] < 0.1]
            if stalled:
                print(f"  ⚠️  {len(stalled)} worker(s) appear stalled (no products)")

            # Check for high resource usage
            total_mem = sum(w['memory_mb'] for w in active_workers)
            total_cpu = sum(w['cpu_percent'] for w in active_workers)

            if total_mem > 8000:
                print(f"  ⚠️  High RAM usage: {total_mem:.0f}MB")
            if total_cpu > 80:
                print(f"  ⚠️  High CPU usage: {total_cpu:.1f}%")

            # Check for blocking
            if stats['blocking_incidents'] > 0:
                print(f"  ⚠️  {stats['blocking_incidents']} blocking incident(s) detected")

            # If everything is good
            if not stalled and total_mem < 8000 and total_cpu < 80:
                print("  ✅ All systems normal")

    print("")
    print("="*70)
    print("")
    print("💡 Commands:")
    print("  Watch live: python check_supervisor_status.py --watch")
    print("  View logs: tail -f scrape_output_supervised/supervisor.log")
    print("  Stop: Ctrl+C in supervisor terminal")
    print("")

    return True

def watch_mode():
    """Continuously monitor supervisor"""
    print("Watching supervisor status (Ctrl+C to exit)...\n")

    try:
        while True:
            # Clear screen (Windows compatible)
            import os
            os.system('cls' if os.name == 'nt' else 'clear')

            check_status()

            # Wait 10 seconds
            print("Refreshing in 10 seconds...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nStopped monitoring")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Check Supervisor Status')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring')
    args = parser.parse_args()

    if args.watch:
        watch_mode()
    else:
        check_status()
