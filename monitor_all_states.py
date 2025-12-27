"""
Monitor All States - Track WA and OR scraping progress

Automatically detects which state(s) are running and displays unified status.

Usage:
    python monitor_all_states.py           # One-time check
    python monitor_all_states.py --watch   # Continuous monitoring
"""

import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime


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


def load_state_status(state):
    """Load status for a specific state (WA or OR)"""
    status_file = Path(f"scrape_output_supervised/{state}/supervisor_status.json")

    if not status_file.exists():
        return None

    # Check if file is recent (supervisor still alive)
    file_age = time.time() - status_file.stat().st_mtime

    with open(status_file) as f:
        status = json.load(f)

    status['file_age'] = file_age
    status['state'] = state

    return status


def display_unified_status():
    """Display unified status for all active states"""

    # Load both states
    wa_status = load_state_status('WA')
    or_status = load_state_status('OR')

    # Also check for old single-state format
    old_status_file = Path("scrape_output_supervised/supervisor_status.json")
    if old_status_file.exists() and not wa_status and not or_status:
        # Old format - try to determine state from workers
        with open(old_status_file) as f:
            old_status = json.load(f)

        # Guess state from first worker's store name
        if old_status.get('workers'):
            first_worker = old_status['workers'][0]
            store_name = first_worker.get('store', '')
            if ', WA' in store_name:
                wa_status = old_status
                wa_status['state'] = 'WA'
            elif ', OR' in store_name:
                or_status = old_status
                or_status['state'] = 'OR'

    if not wa_status and not or_status:
        print("❌ No active scraping detected")
        print("\nStart with:")
        print("  All states: python run_all_stores.py --max-workers 8")
        print("  WA only:    python intelligent_supervisor.py --state WA --max-workers 8")
        print("  OR only:    python intelligent_supervisor.py --state OR --max-workers 8")
        return False

    print("="*70)
    print("MULTI-STATE SCRAPING STATUS")
    print("="*70)
    print(f"Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Combined stats
    total_products = 0
    total_workers = 0
    total_launched = 0

    # Display each active state
    for status in [wa_status, or_status]:
        if not status:
            continue

        state = status['state']
        stats = status['stats']
        workers = status['workers']

        # Check if supervisor is stale
        if status['file_age'] > 120:
            print(f"⚠️  {state} SUPERVISOR: Status file is {status['file_age']:.0f}s old (might have crashed)")
            print()
            continue

        last_update = datetime.fromisoformat(status['timestamp'])
        now = datetime.now()
        update_ago = (now - last_update).total_seconds()

        print(f"🌲 {state} STATE")
        print(f"   Last Update: {format_duration(update_ago)} ago")
        print(f"   Uptime: {format_duration(status['uptime_seconds'])}")
        print(f"   Products: {stats['total_products']:,}")
        print(f"   Workers: {stats['current_workers']}/{stats['workers_launched']} launched")

        # Update totals
        total_products += stats['total_products']
        total_workers += stats['current_workers']
        total_launched += stats['workers_launched']

        # Show active workers
        active_workers = [w for w in workers if w['alive']]
        if active_workers:
            print(f"   Active Workers:")
            for w in active_workers:
                status_icon = "✅"
                rate = w['products_per_min']
                if rate < 0.1:
                    status_icon = "⚠️"

                print(f"     {status_icon} Worker {w['id']}: {w['store']}")
                print(f"        {w['products']:,} products ({rate:.1f}/min) | {w['memory_mb']:.0f}MB | {w['cpu_percent']:.1f}% CPU")

        # Health indicators
        if stats['blocking_incidents'] > 0:
            print(f"   ⚠️  Blocking incidents: {stats['blocking_incidents']}")

        print()

    # Combined summary
    print("="*70)
    print("📊 COMBINED TOTALS")
    print(f"   Total Products: {total_products:,}")
    print(f"   Active Workers: {total_workers}")
    print(f"   Workers Launched: {total_launched}")

    # Calculate combined rate
    if wa_status or or_status:
        combined_uptime = 0
        if wa_status:
            combined_uptime += wa_status['uptime_seconds']
        if or_status:
            combined_uptime += or_status['uptime_seconds']

        if combined_uptime > 0:
            avg_rate = (total_products / combined_uptime) * 3600
            print(f"   Average Rate: {avg_rate:.0f} products/hour")

    print()
    print("="*70)
    print()
    print("💡 Commands:")
    print("  Watch live: python monitor_all_states.py --watch")
    print("  WA logs:    tail -f scrape_output_supervised/WA/supervisor.log")
    print("  OR logs:    tail -f scrape_output_supervised/OR/supervisor.log")
    print("  Stop:       Ctrl+C in supervisor terminal")
    print()

    return True


def watch_mode():
    """Continuously monitor all states"""
    print("Watching all states (Ctrl+C to exit)...\n")

    try:
        while True:
            # Clear screen (Windows compatible)
            os.system('cls' if os.name == 'nt' else 'clear')

            display_unified_status()

            # Wait 10 seconds
            print("Refreshing in 10 seconds...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nStopped monitoring")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Monitor All States')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring')
    args = parser.parse_args()

    if args.watch:
        watch_mode()
    else:
        display_unified_status()
