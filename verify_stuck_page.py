"""
Verify Stuck Page and DOM Structure
Following AKAMAI_BYPASS_KNOWLEDGE.md
"""
import asyncio
import os
import sys
import random
import time

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'PARALLEL'))

from playwright.async_api import async_playwright
from scraper import human_mouse_move, human_scroll, warmup_session, apply_pickup_filter

async def debug_lowes():
    print("🚀 Starting Lowe's Debug (Anti-Akamai Mode)...")
    
    async with async_playwright() as p:
        # 1. Setup persistent context
        profile_dir = os.path.join(os.getcwd(), ".playwright-profile", "debug_profile")
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)
            
        launch_kwargs = {
            "headless": False,
            "channel": "chrome",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--start-maximized"
            ]
        }
        
        context = await p.chromium.launch_persistent_context(profile_dir, **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            # 2. Warmup (using actual scraper function)
            print("🏠 Warming up session...")
            await warmup_session(page)
            
            # 3. Navigate to the problematic URL
            print("🔗 Navigating to the problematic URL...")
            target_url = "https://www.lowes.com/pl/caulking/caulk/interior-paint-trim/4294729414-1411293683550?offset=72"
            await page.goto(target_url, wait_until='domcontentloaded', timeout=120000)
            print("⏳ Waiting for content load (10s)...")
            await asyncio.sleep(10)
            
            # Check for Access Denied
            title = await page.title()
            print(f"📄 Page Title: {title}")
            if "Access Denied" in title:
                print("❌ FAILED: Still blocked by Akamai.")
                await page.screenshot(path="akamai_block_v2.png")
                return

            # 4. Try applying pickup filter (the part that was failing/misclicking)
            print("🔘 Attempting to apply pickup filter...")
            result = await apply_pickup_filter(page, "Verification Test")
            print(f"✅ Filter result: {result}")
            
            # 5. Inspect the DOM
            print("🔎 Final DOM Inspection...")
            
            # 5.1 Check for "0 Products"
            body_text = await page.evaluate("document.body.innerText")
            is_empty = "0 Products" in body_text or "0 results" in body_text
            print(f"❓ Is page empty? {is_empty}")
            
            # 5.2 Find Sidebar Filters
            print("📂 Checking Sidebar Filters...")
            
            # Find the "Pickup Today" checkbox
            pickup_elements = await page.evaluate("""() => {
                const results = [];
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (/Pickup Today/i.test(label.innerText)) {
                        const input = label.querySelector('input') || document.getElementById(label.getAttribute('for'));
                        results.push({
                            text: label.innerText,
                            html: label.outerHTML.substring(0, 200),
                            hasInput: !!input,
                            inputId: input ? input.id : null,
                            parentHtml: label.parentElement.outerHTML.substring(0, 200)
                        });
                    }
                }
                return results;
            }""")
            print(f"📦 Found {len(pickup_elements)} elements matching 'Pickup Today'")
            for el in pickup_elements:
                print(f"   - Label: {el['text']}")
                print(f"   - Parent: {el['parentHtml']}")

            # Find the "Interior paint & trim" checkbox
            interior_elements = await page.evaluate("""() => {
                const results = [];
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (/Interior paint/i.test(label.innerText)) {
                        results.push({
                            text: label.innerText,
                            html: label.outerHTML.substring(0, 200),
                            parentClasses: label.parentElement.className
                        });
                    }
                }
                return results;
            }""")
            print(f"🎨 Found {len(interior_elements)} elements matching 'Interior paint'")
            for el in interior_elements:
                print(f"   - Label: {el['text']}")

            # 6. Screenshot the sidebar
            await page.screenshot(path="lowes_sidebar_debug.png", full_page=False)
            print("📸 Screenshot saved to lowes_sidebar_debug.png")

            # 7. Done
            print("✨ Debug session completed successfully!")

        except Exception as e:
            print(f"❌ ERROR: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_lowes())
