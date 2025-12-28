"""
SYSTEMATIC TEST SUITE FOR GLOORBOT ANTI-DETECTION

This script runs multiple browser configurations and reports which ones
successfully load Lowe's without getting blocked.

Run with: python systematic_tests.py
"""
import asyncio
import shutil
from pathlib import Path
from datetime import datetime

# Test configurations
TESTS = {
    "A_chrome_no_stealth": {
        "description": "Chrome channel, NO stealth (like PARALLEL)",
        "channel": "chrome",
        "use_stealth": False,
    },
    "B_chromium_no_stealth": {
        "description": "Chromium, NO stealth",
        "channel": None,  # Default Chromium
        "use_stealth": False,
    },
    "C_chromium_stealth_async": {
        "description": "Chromium + stealth_async (v0.5.0 pattern)",
        "channel": None,
        "use_stealth": True,
        "stealth_method": "async",
    },
    "D_chromium_stealth_hook": {
        "description": "Chromium + hook_playwright_context (OLD broken pattern)",
        "channel": None,
        "use_stealth": True,
        "stealth_method": "hook",
    },
}

async def run_test(test_name: str, config: dict) -> dict:
    """Run a single test configuration and return results."""
    from playwright.async_api import async_playwright
    
    print(f"\n{'='*60}")
    print(f"TEST {test_name}: {config['description']}")
    print(f"{'='*60}")
    
    # Clean profile for fresh test
    profile_dir = Path(f"test_profiles/{test_name}")
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        "test": test_name,
        "config": config["description"],
        "webdriver_before": None,
        "webdriver_after": None,
        "page_title": None,
        "blocked": None,
        "error": None,
    }
    
    try:
        async with async_playwright() as p:
            # Base launch kwargs
            launch_kwargs = {
                "headless": False,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-infobars",
                    "--lang=en-US",
                    "--no-default-browser-check",
                    "--start-maximized",
                    "--window-size=1440,960",
                ],
                "slow_mo": 12,
                "viewport": {"width": 1440, "height": 900},
                "locale": "en-US",
                "timezone_id": "America/Los_Angeles",
            }
            
            # Add channel if specified
            if config.get("channel"):
                launch_kwargs["channel"] = config["channel"]
            
            # Apply hook-style stealth BEFORE launch (old pattern)
            if config.get("use_stealth") and config.get("stealth_method") == "hook":
                try:
                    from playwright_stealth import Stealth
                    stealth = Stealth(
                        navigator_languages_override=("en-US", "en"),
                        navigator_platform_override="Win32",
                        navigator_vendor_override="Google Inc.",
                    )
                    stealth.hook_playwright_context(p)
                    print("  [Stealth] Applied hook_playwright_context (old pattern)")
                except Exception as e:
                    print(f"  [Stealth] Hook failed: {e}")
            
            # Launch browser
            print(f"  [Browser] Launching with channel={config.get('channel', 'chromium')}")
            context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Apply async stealth AFTER page creation (new pattern)
            if config.get("use_stealth") and config.get("stealth_method") == "async":
                try:
                    from playwright_stealth import stealth_async
                    await stealth_async(page)
                    print("  [Stealth] Applied stealth_async (new pattern)")
                except Exception as e:
                    print(f"  [Stealth] stealth_async failed: {e}")
            
            # Check webdriver BEFORE navigation
            result["webdriver_before"] = await page.evaluate("navigator.webdriver")
            print(f"  [Check] navigator.webdriver BEFORE navigation: {result['webdriver_before']}")
            
            # Navigate to Lowe's
            print("  [Nav] Going to https://www.lowes.com/")
            await page.goto("https://www.lowes.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            
            # Check webdriver AFTER navigation
            result["webdriver_after"] = await page.evaluate("navigator.webdriver")
            print(f"  [Check] navigator.webdriver AFTER navigation: {result['webdriver_after']}")
            
            # Get page title
            result["page_title"] = await page.title()
            print(f"  [Result] Page title: {result['page_title']}")
            
            # Check if blocked
            blocked_keywords = ["pardon", "access denied", "robot", "blocked", "verify"]
            result["blocked"] = any(kw in result["page_title"].lower() for kw in blocked_keywords)
            
            # Screenshot
            screenshot_path = f"test_results/{test_name}.png"
            Path("test_results").mkdir(exist_ok=True)
            await page.screenshot(path=screenshot_path)
            print(f"  [Screenshot] Saved to {screenshot_path}")
            
            await context.close()
            
    except Exception as e:
        result["error"] = str(e)
        print(f"  [ERROR] {e}")
    
    # Print result
    if result["blocked"]:
        print(f"  >>> RESULT: BLOCKED <<<")
    elif result["error"]:
        print(f"  >>> RESULT: ERROR <<<")
    else:
        print(f"  >>> RESULT: SUCCESS <<<")
    
    return result


async def main():
    print("\n" + "="*70)
    print("GLOORBOT SYSTEMATIC ANTI-DETECTION TESTS")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*70)
    
    results = []
    
    for test_name, config in TESTS.items():
        result = await run_test(test_name, config)
        results.append(result)
        
        # Pause between tests
        print("\n  [Pause] Waiting 5 seconds before next test...")
        await asyncio.sleep(5)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"{'Test':<30} {'Blocked':<10} {'webdriver':<15} {'Title':<30}")
    print("-"*70)
    for r in results:
        blocked_str = "BLOCKED" if r["blocked"] else ("ERROR" if r["error"] else "OK")
        wd = str(r["webdriver_before"])
        title = (r["page_title"] or "N/A")[:28]
        print(f"{r['test']:<30} {blocked_str:<10} {wd:<15} {title:<30}")
    
    # Recommendation
    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    working = [r for r in results if not r["blocked"] and not r["error"]]
    if working:
        print(f"Use configuration from test: {working[0]['test']}")
        print(f"Description: {working[0]['config']}")
    else:
        print("No configuration worked! Need to investigate further.")
    
    # Save results
    import json
    Path("test_results").mkdir(exist_ok=True)
    with open("test_results/summary.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to test_results/summary.json")


if __name__ == "__main__":
    asyncio.run(main())
