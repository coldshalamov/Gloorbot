"""
Quick test of the intelligent scraper setup
Tests with 2 stores for 5 minutes to verify everything works
"""

import asyncio
import sys
from pathlib import Path

print("="*70)
print("INTELLIGENT SCRAPER - QUICK TEST")
print("="*70)
print("\nThis will test the orchestrator with 2 stores for 5 minutes")
print("to verify everything is working correctly.\n")

# Check dependencies
print("Checking dependencies...")

try:
    import openai
    print("✅ OpenAI SDK installed")
    has_openai = True
except ImportError:
    print("⚠️  OpenAI SDK not installed (AI mode unavailable)")
    print("   Install with: pip install openai")
    has_openai = False

# Check files exist
required_files = [
    'intelligent_scraper.py',
    'run_single_store.py',
    'LowesMap.txt',
    'apify_actor_seed/src/main.py'
]

print("\nChecking required files...")
all_files_exist = True
for file in required_files:
    exists = Path(file).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {file}")
    if not exists:
        all_files_exist = False

if not all_files_exist:
    print("\n❌ Missing required files! Cannot proceed.")
    sys.exit(1)

print("\n✅ All required files present")

# Check Chrome installation
print("\nChecking Chrome browser...")
import subprocess
try:
    result = subprocess.run(['where', 'chrome'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Chrome found:", result.stdout.split('\n')[0])
    else:
        print("⚠️  Chrome not found in PATH")
        print("   The scraper needs Chrome (not Chromium)")
except Exception as e:
    print(f"⚠️  Could not check Chrome: {e}")

print("\n" + "="*70)
print("STARTING TEST RUN")
print("="*70)
print("\nConfiguration:")
print("  State: WA")
print("  Max Workers: 2")
print("  Duration: Will run until 2 stores complete or you press Ctrl+C")
print("  AI Mode: Disabled (use --use-ai to enable)")
print("\nPress Ctrl+C at any time to stop")
print("="*70 + "\n")

input("Press Enter to start the test run...")

# Import and run the orchestrator
try:
    from intelligent_scraper import IntelligentOrchestrator

    async def test_run():
        orchestrator = IntelligentOrchestrator(
            state='WA',
            max_workers=2,
            use_ai=False
        )

        # Override to only use 2 stores for testing
        original_load = orchestrator.load_stores
        def load_test_stores():
            original_load()
            orchestrator.stores = orchestrator.stores[:2]  # Only first 2 stores
            print(f"\n📋 Test limited to {len(orchestrator.stores)} stores:")
            for store in orchestrator.stores:
                print(f"   - {store['name']}")

        orchestrator.load_stores = load_test_stores

        await orchestrator.run()

    asyncio.run(test_run())

except KeyboardInterrupt:
    print("\n\n⚠️  Test interrupted by user")
    print("="*70)
except Exception as e:
    print(f"\n\n❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    print("="*70)
    sys.exit(1)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nCheck scrape_output_parallel/ for results")
print("\nIf the test worked, you can run the full scraper with:")
print("  python intelligent_scraper.py --state WA --max-workers 10")
print("="*70)
