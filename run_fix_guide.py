"""
STEP-BY-STEP EXECUTION GUIDE FOR FIXING GLOORBOT

Run this script and follow the instructions.
Each step will either auto-execute or prompt you for input.
"""
import subprocess
import sys
from pathlib import Path

def print_header(step_num, title):
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*70}\n")

def wait_for_user(message="Press Enter to continue..."):
    input(f"\n>>> {message}")

def run_command(cmd, description):
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
        return False
    print(f"SUCCESS")
    if result.stdout.strip():
        print(result.stdout[:500])
    return True

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           GLOORBOT ANTI-DETECTION FIX - EXECUTION GUIDE              ║
╠══════════════════════════════════════════════════════════════════════╣
║  This guide will walk you through fixing the blocking issue.         ║
║  We will test each configuration methodically until we find one      ║
║  that works, then apply it to the worker and build.                  ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    wait_for_user("Ready to begin?")
    
    # STEP 1: Clean test environment
    print_header(1, "CLEAN TEST ENVIRONMENT")
    print("Removing old test profiles and results...")
    
    for folder in ["test_profiles", "test_results", "test_profile_v4", "test_profile_v5"]:
        p = Path(folder)
        if p.exists():
            import shutil
            shutil.rmtree(p)
            print(f"  Deleted: {folder}")
    print("Done.")
    
    # STEP 2: Run systematic tests
    print_header(2, "RUN SYSTEMATIC TESTS")
    print("""
We will now test 4 different browser configurations:
  A. Chrome channel, no stealth (like PARALLEL)
  B. Chromium, no stealth  
  C. Chromium + stealth_async (the v0.5.0 pattern)
  D. Chromium + hook_playwright_context (the old broken pattern)

This will open 4 browser windows one after another.
Watch each one to see if it gets blocked or loads successfully.
    """)
    
    wait_for_user("Ready to run the tests?")
    
    # Run the systematic tests
    result = subprocess.run([sys.executable, "systematic_tests.py"], cwd=Path(__file__).parent)
    
    if result.returncode != 0:
        print("\nTests encountered an error. Check the output above.")
    
    # STEP 3: Analyze results
    print_header(3, "ANALYZE RESULTS")
    print("Check the test_results folder for screenshots and summary.json")
    print("Look at which configurations succeeded vs failed.")
    
    results_file = Path("test_results/summary.json")
    if results_file.exists():
        import json
        with open(results_file) as f:
            results = json.load(f)
        
        print("\nRESULTS SUMMARY:")
        print("-" * 50)
        for r in results:
            status = "BLOCKED" if r.get("blocked") else ("ERROR" if r.get("error") else "SUCCESS")
            print(f"  {r['test']}: {status}")
        
        working = [r for r in results if not r.get("blocked") and not r.get("error")]
        if working:
            print(f"\n✅ WORKING CONFIGURATION FOUND: {working[0]['test']}")
            print(f"   Description: {working[0]['config']}")
        else:
            print("\n❌ NO WORKING CONFIGURATION FOUND")
            print("   We need to try additional approaches.")
    
    # STEP 4: Decision point
    print_header(4, "DECISION POINT")
    print("""
Based on the test results:

If Test A (Chrome channel) worked:
  → We should use Chrome channel like PARALLEL does
  → This requires Chrome to be installed on user machines

If Test C (Chromium + stealth_async) worked:
  → v0.5.0 fix is correct, just need to build and test

If nothing worked:
  → We need to try CDP connection to system Chrome
  → Or investigate Cheapskater's exact configuration more deeply
    """)
    
    wait_for_user("Review the results, then press Enter to continue...")
    
    # STEP 5: Next actions
    print_header(5, "NEXT ACTIONS")
    print("""
Based on your test results, here are the next steps:

OPTION 1: If Chromium + stealth_async worked (Test C)
  → v0.5.0 is building on GitHub Actions
  → Wait for build to complete
  → Download and test WorkerSetup.exe

OPTION 2: If only Chrome channel worked (Test A)
  → Need to modify slot_worker.py to use channel="chrome"
  → Push v0.6.0 with Chrome requirement
  → Users will need Chrome installed

OPTION 3: If nothing worked
  → We need deeper investigation
  → Consider CDP connection approach
  → Or exact Cheapskater configuration copy

Tell Antigravity which option to proceed with.
    """)
    
    print("\n" + "="*70)
    print("GUIDE COMPLETE")
    print("="*70)
    print("\nShare your test results with Antigravity to proceed.")


if __name__ == "__main__":
    main()
