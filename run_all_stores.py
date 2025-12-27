"""
Run All Stores - WA and OR Complete Scraping

This runs the intelligent supervisor for both WA and OR states sequentially.
Products are saved to separate output directories for organization.

Usage:
    python run_all_stores.py --max-workers 8
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
from intelligent_supervisor import IntelligentSupervisor


async def run_both_states(max_workers, check_interval):
    """Run WA stores, then OR stores"""

    print("="*70)
    print("COMPLETE STORE SCRAPING - WA + OR")
    print("="*70)
    print(f"Max Workers: {max_workers}")
    print(f"Check Interval: {check_interval}s")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()

    # Phase 1: Washington (35 stores)
    print("🌲 PHASE 1: WASHINGTON STORES")
    print("="*70)

    wa_supervisor = IntelligentSupervisor(
        state='WA',
        max_workers=max_workers,
        check_interval=check_interval
    )

    # Create WA-specific output directory
    wa_output = Path("scrape_output_supervised/WA")
    wa_output.mkdir(parents=True, exist_ok=True)
    wa_supervisor.output_dir = wa_output
    wa_supervisor.status_file = wa_output / "supervisor_status.json"

    await wa_supervisor.run()

    wa_products = wa_supervisor.stats['total_products']
    wa_runtime = (wa_supervisor.stats.get('end_time', 0) or 0) - wa_supervisor.stats['start_time']

    print()
    print("="*70)
    print(f"✅ WASHINGTON COMPLETE: {wa_products:,} products in {wa_runtime/3600:.1f} hours")
    print("="*70)
    print()

    # Phase 2: Oregon (14 stores)
    print("🌲 PHASE 2: OREGON STORES")
    print("="*70)

    or_supervisor = IntelligentSupervisor(
        state='OR',
        max_workers=max_workers,
        check_interval=check_interval
    )

    # Create OR-specific output directory
    or_output = Path("scrape_output_supervised/OR")
    or_output.mkdir(parents=True, exist_ok=True)
    or_supervisor.output_dir = or_output
    or_supervisor.status_file = or_output / "supervisor_status.json"

    await or_supervisor.run()

    or_products = or_supervisor.stats['total_products']
    or_runtime = (or_supervisor.stats.get('end_time', 0) or 0) - or_supervisor.stats['start_time']

    print()
    print("="*70)
    print(f"✅ OREGON COMPLETE: {or_products:,} products in {or_runtime/3600:.1f} hours")
    print("="*70)
    print()

    # Final Summary
    total_products = wa_products + or_products
    total_runtime = wa_runtime + or_runtime

    print()
    print("="*70)
    print("🎉 ALL STORES COMPLETE!")
    print("="*70)
    print(f"Total Stores: 49 (35 WA + 14 OR)")
    print(f"Total Products: {total_products:,}")
    print(f"Total Runtime: {total_runtime/3600:.1f} hours")
    print(f"Average Rate: {total_products/(total_runtime/3600):.0f} products/hour")
    print()
    print("📁 Output Locations:")
    print(f"   WA: scrape_output_supervised/WA/worker_*.jsonl")
    print(f"   OR: scrape_output_supervised/OR/worker_*.jsonl")
    print()
    print("🔄 Next Steps:")
    print("   1. Merge outputs: cat scrape_output_supervised/WA/worker_*.jsonl scrape_output_supervised/OR/worker_*.jsonl > products_all.jsonl")
    print("   2. Analyze: python analyze_url_redundancy.py products_all.jsonl")
    print("="*70)


async def main():
    parser = argparse.ArgumentParser(description='Run All Stores (WA + OR)')
    parser.add_argument('--max-workers', type=int, default=8, help='Max workers per state')
    parser.add_argument('--check-interval', type=int, default=60, help='Check every N seconds')
    args = parser.parse_args()

    await run_both_states(args.max_workers, args.check_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
        sys.exit(0)
