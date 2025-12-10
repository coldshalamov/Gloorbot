"""
Run All Validation Tests

This is a convenience wrapper that runs all validation tests
and provides a clean summary output.
"""

import subprocess
import sys


def run_validation():
    """Run the final validation test suite."""
    print("Starting validation tests...")
    print()

    result = subprocess.run(
        [sys.executable, "test_final_validation.py"],
        capture_output=False,
        text=True
    )

    return result.returncode


if __name__ == "__main__":
    exit_code = run_validation()

    if exit_code == 0:
        print("\n" + "="*60)
        print("[OK] VALIDATION COMPLETE - ACTOR IS READY")
        print("="*60)
        print("\nNext steps:")
        print("1. Read QUICK_START.md")
        print("2. Deploy: apify push")
        print("3. Test: apify call lowes-pickup-today-scraper")
    else:
        print("\n" + "="*60)
        print("[WARN] VALIDATION INCOMPLETE")
        print("="*60)
        print("\nSome tests failed. Review errors above.")

    sys.exit(exit_code)
