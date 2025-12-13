"""
Quick Test Script for Optimized Lowe's Scraper

This script tests the optimized scraper with a small subset of data
to validate it works before running the full 109K URL crawl.

Test Configuration:
- 2 stores (instead of 50)
- 3 categories (instead of 291)
- 2 pages per category (instead of 20)
- Total: 2 × 3 × 2 = 12 URLs (instead of 109,000)

Expected Results:
- 2 browsers launched (one per store)
- 4 concurrent pages per browser = 8 parallel workers
- Should complete in < 5 minutes
- Should find products from both stores
- Cost: < $1
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from apify import Actor


async def test_optimized_scraper():
    """Run a small test of the optimized scraper."""
    
    # Override Actor.get_input for testing
    test_input = {
        # Test with 2 stores
        "store_ids": [],  # Will load from LowesMap.txt but limit to 2
        
        # Test with 3 categories
        "categories": [
            "https://www.lowes.com/pl/Power-tools-Tools/4294607949",
            "https://www.lowes.com/pl/Hand-tools-Tools/4294607947",
            "https://www.lowes.com/pl/Tool-storage-Tools/4294607951",
        ],
        
        # Only 2 pages per category
        "max_pages_per_category": 2,
        
        # Use stealth
        "use_stealth": True,
        
        # US proxies
        "proxy_country": "US",
    }
    
    print("=" * 80)
    print("OPTIMIZED LOWE'S SCRAPER - TEST RUN")
    print("=" * 80)
    print(f"\nTest Configuration:")
    print(f"  Stores: 2 (limited from LowesMap.txt)")
    print(f"  Categories: {len(test_input['categories'])}")
    print(f"  Pages per category: {test_input['max_pages_per_category']}")
    print(f"  Total URLs: 2 × 3 × 2 = 12")
    print(f"\nExpected:")
    print(f"  Browser instances: 2 (vs 12 in old version)")
    print(f"  Concurrent workers: 2 browsers × 4 pages = 8")
    print(f"  Runtime: < 5 minutes")
    print(f"  Cost: < $1")
    print("\n" + "=" * 80)
    print("\nStarting test...\n")
    
    # Import and run the optimized main
    from main_optimized import main
    
    # Monkey-patch Actor.get_input to return our test input
    original_get_input = Actor.get_input
    
    async def mock_get_input():
        return test_input
    
    Actor.get_input = mock_get_input
    
    try:
        await main()
    finally:
        Actor.get_input = original_get_input
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)
    print("\nNext Steps:")
    print("  1. Review the output above for any errors")
    print("  2. Check that 2 browsers were created")
    print("  3. Verify products were extracted")
    print("  4. If successful, deploy to Apify with full configuration")
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_optimized_scraper())
